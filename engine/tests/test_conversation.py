"""Conversation contracts using frozen local article fixtures and a fake model only."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from eis_engine.contracts import ChatReply, ChatSend, Failure
from eis_engine.service import Service
from eis_engine.storage import Store, encode, now, uid


class FakeChatModel:
    def __init__(self):
        self.calls = []
        self.reply = ChatReply(message="لنناقش الزاوية أولًا.")
        self.started = asyncio.Event()
        self.release = None

    async def run(self, profile, instructions, payload, schema):
        self.calls.append((dict(profile), instructions, payload))
        self.started.set()
        if self.release is not None:
            await self.release.wait()
        return self.reply


@pytest.fixture
def service(tmp_path, monkeypatch):
    s = Service(Store(tmp_path), FakeChatModel())
    articles = {}
    monkeypatch.setattr(s.news, "snapshot", lambda: {"articles": list(articles.values())})
    monkeypatch.setattr(s.news, "article", lambda identifier, mark_read=False: dict(articles[identifier]))
    s.test_articles = articles
    yield s
    s.store.close()


async def setup(s, **kwargs):
    profile = await s.dispatch("providers.save", {"provider_key": "openai", "model_id": "chat-test"})
    pid = profile["profile_id"]
    with s.db:
        s.db.execute("INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)", (pid, s.ws, encode([{"id": "chat-test", "available": True}]), "fixture", now(), None, 9999999999))
    cid = (await s.dispatch("chat.create", {}))["conversation_id"]
    return {"conversation_id": cid, "profile_id": pid, "model_id": "chat-test", "message": "ناقش هذه الفكرة", "consent": True, "idempotency_key": uid(), "include_news": False, **kwargs}


def article(s, stamp=None, **kwargs):
    identifier = uid()
    item = {"id": identifier, "title": "خبر اختبار", "url": "https://example.org/story/" + identifier, "source_title": "مصدر اختبار", "published_at": stamp, "discovered_at": now(), "body_status": "full", "text": "مادة الخبر الأصلية", **kwargs}
    s.test_articles[identifier] = item
    subscription = uid()
    with s.db:
        s.db.execute("INSERT INTO news_subscriptions(id,workspace_id,title,url,feed_url,kind,created_at) VALUES(?,?,?,?,?,?,?)", (subscription,s.ws,"Test feed","https://example.org/"+subscription,"https://example.org/feed/"+subscription,"rss",now()))
        s.db.execute("INSERT INTO news_articles(id,workspace_id,subscription_id,guid,title,url,published_at,discovered_at,summary,text,body_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (identifier,s.ws,subscription,identifier,item["title"],item["url"],item["published_at"],item["discovered_at"],item.get("summary",""),item["text"],item["body_status"]))
    return identifier


async def finish(s, payload):
    submitted = await s.dispatch("chat.send", payload)
    await s.tasks[submitted["job_id"]]
    return await s.dispatch("jobs.get", {"job_id": submitted["job_id"]})


def test_weekly_window_excludes_unknown_old_future_and_naive_dates(service):
    async def scenario():
        current = datetime.now(timezone.utc)
        good = article(service, (current - timedelta(days=2)).isoformat())
        for stamp in [None, "nonsense", (current - timedelta(days=8)).isoformat(), (current + timedelta(days=2)).isoformat(), current.replace(tzinfo=None).isoformat()]:
            article(service, stamp)
        payload = await setup(service, include_news=True, days=7)
        context = service.conversations.source_context(ChatSend.model_validate(payload))
        assert [a["id"] for a in context["news"]] == [good]
        assert context["window"]["selected_explicitly"] is False
        assert context["news"][0]["published_at"] == service.test_articles[good]["published_at"]
        assert context["news"][0]["discovered_at"] == service.test_articles[good]["discovered_at"]
    asyncio.run(scenario())


def test_style_samples_are_separate_from_news_and_require_rights(service):
    async def scenario():
        payload = await setup(service)
        owned = await service.dispatch("sources.add", {"title": "كتابتي", "text": "طريقتي في الشرح", "rights_status": "owned", "purpose": "style"})
        await service.dispatch("sources.add", {"title": "مرجع", "text": "حقيقة من مرجع", "rights_status": "owned", "purpose": "reference"})
        with pytest.raises(Failure):
            await service.dispatch("sources.add", {"title": "غير مرخص", "text": "نص غير مرخص", "rights_status": "unknown", "purpose": "style"})
        context = service.conversations.source_context(ChatSend.model_validate(payload))
        assert context["news"] == []
        assert [x["id"] for x in context["style_samples"]] == [owned["item_id"]]
        assert context["style_samples"][0]["version_id"] == owned["version_id"]
    asyncio.run(scenario())


def test_chat_submission_is_idempotent_and_one_active_message_per_conversation(service):
    async def scenario():
        payload = await setup(service)
        service.factory.release = asyncio.Event()
        first = await service.dispatch("chat.send", payload)
        second = await service.dispatch("chat.send", payload)
        assert first["job_id"] == second["job_id"]
        with pytest.raises(Failure) as busy:
            await service.dispatch("chat.send", {**payload, "message": "رسالة أخرى", "idempotency_key": uid()})
        assert busy.value.code == "BUSY"
        with pytest.raises(Failure):
            await service.dispatch("chat.send", {**payload, "message": "تغيير نفس الطلب"})
        task = service.tasks[first["job_id"]]
        service.factory.release.set()
        await task
        messages = (await service.dispatch("chat.detail", {"conversation_id": payload["conversation_id"]}))["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant"]
    asyncio.run(scenario())


def test_unknown_article_id_rejects_entire_reply_without_artifacts(service):
    async def scenario():
        aid = article(service, now())
        payload = await setup(service, include_news=True, article_ids=[aid])
        service.factory.reply = ChatReply(message="جواب", article_ids=[uid()], drafts=[{"title": "مسودة", "text": "نص", "format": "x_post", "article_ids": [aid]}])
        job = await finish(service, payload)
        assert job["state"] == "failed" and job["error_code"] == "VALIDATION_ERROR"
        assert service.store.rows("SELECT id FROM drafts") == []
        assert service.store.rows("SELECT id FROM chat_messages WHERE role='assistant'") == []
    asyncio.run(scenario())


def test_new_draft_does_not_overwrite_working_draft_and_keeps_source_provenance(service):
    async def scenario():
        original = await service.dispatch("drafts.create", {"topic": "الأصل", "text": "نصي المحفوظ"})
        aid = article(service, now(), body_status="summary")
        payload = await setup(service, include_news=True, article_ids=[aid], format="x_posts", draft_title="الأصل", draft_text="تعديلات لم تحفظ")
        service.factory.reply = ChatReply(message="صياغة مقترحة", drafts=[{"title": "اقتراح", "text": "نص جديد", "format": "x_post", "article_ids": [aid]}])
        job = await finish(service, payload)
        assert job["state"] == "completed"
        new_id = json.loads(job["result_json"])["draft_ids"][0]
        assert new_id != original["draft_id"]
        old = await service.dispatch("drafts.detail", {"draft_id": original["draft_id"]})
        assert old["versions"][0]["text"] == "نصي المحفوظ"
        new = await service.dispatch("drafts.detail", {"draft_id": new_id})
        assert new["news_evidence"][0]["article_id"] == aid
        assert new["news_evidence"][0]["published_at"] == service.test_articles[aid]["published_at"]
        assert any("ملخص" in x for x in json.loads(new["versions"][0]["warnings_json"]))
    asyncio.run(scenario())


def test_context_is_frozen_before_feed_changes(service):
    async def scenario():
        aid = article(service, now())
        payload = await setup(service, include_news=True, article_ids=[aid])
        service.factory.release = asyncio.Event()
        submitted = await service.dispatch("chat.send", payload)
        service.test_articles[aid]["text"] = "خبر تغير بعد الإرسال"
        task = service.tasks[submitted["job_id"]]
        service.factory.release.set()
        await task
        assert service.factory.calls[0][2]["news"][0]["text"] == "مادة الخبر الأصلية"
    asyncio.run(scenario())


def test_cancel_and_stale_resume_preserve_conversation(service):
    async def scenario():
        payload = await setup(service)
        service.factory.release = asyncio.Event()
        first = await service.dispatch("chat.send", payload)
        await service.factory.started.wait()
        cancelled = await service.dispatch("jobs.cancel", {"job_id": first["job_id"]})
        assert cancelled["state"] == "cancelled"
        assert service.store.rows("SELECT id FROM chat_messages WHERE role='assistant'") == []
        assert service.store.rows("SELECT id FROM drafts") == []
        service.factory.release = None
        second = await finish(service, {**payload, "idempotency_key": uid(), "message": "نقاش أحدث"})
        assert second["state"] == "completed"
        with pytest.raises(Failure) as stale:
            await service.dispatch("jobs.resume", {"job_id": first["job_id"], "consent": True})
        assert stale.value.code == "STALE_CONTEXT"
    asyncio.run(scenario())


def test_explicit_consent_is_required_and_missing_consent_writes_nothing(service):
    async def scenario():
        payload = await setup(service, consent=False)
        with pytest.raises(Failure) as error:
            await service.dispatch("chat.send", payload)
        assert error.value.code == "PERMISSION_DENIED"
        assert service.store.rows("SELECT id FROM chat_messages") == []
        assert service.store.rows("SELECT id FROM jobs") == []
    asyncio.run(scenario())


def test_empty_news_does_not_create_fabricated_news_drafts(service):
    async def scenario():
        payload = await setup(service, include_news=True, format="x_posts", message="اكتب أخبار الأسبوع")
        service.factory.reply = ChatReply(message="خبر غير مستند", drafts=[{"title": "خبر مختلق", "text": "حدث شيء اليوم", "format": "x_post"}])
        job = await finish(service, payload)
        assert service.store.rows("SELECT id FROM drafts") == []
        assert len(service.factory.calls) == 1
        assert job["state"] == "failed"
    asyncio.run(scenario())


def test_draft_records_style_rules_used_at_submission_not_completion(service):
    async def scenario():
        imported = await service.dispatch("sources.add", {"title": "أسلوبي", "text": "كيف تشرح ببساطة؟", "rights_status": "owned", "purpose": "style"})
        analysis = await service.dispatch("analysis.run", {"item_ids": [imported["item_id"]], "idempotency_key": uid()})
        await service.tasks[analysis["job_id"]]
        technique = service.snapshot()["techniques"][0]["id"]
        await service.dispatch("dna.approve", {"technique_id": technique})
        rule = service.snapshot()["rules"][0]
        payload = await setup(service, message="اكتب فكرة عامة", include_news=False)
        service.factory.release = asyncio.Event()
        service.factory.reply = ChatReply(message="اقتراح", drafts=[{"title": "فكرة", "text": "نص بأسلوبي", "format": "x_post"}])
        submitted = await service.dispatch("chat.send", payload)
        await service.dispatch("dna.retire", {"rule_id": rule["id"]})
        task = service.tasks[submitted["job_id"]]
        service.factory.release.set()
        await task
        job = await service.dispatch("jobs.get", {"job_id": submitted["job_id"]})
        assert job["state"] == "completed"
        draft_id = json.loads(job["result_json"])["draft_ids"][0]
        detail = await service.dispatch("drafts.detail", {"draft_id": draft_id})
        recorded = service.require("dna_versions", detail["versions"][0]["dna_version_id"])
        assert any(x["id"] == rule["id"] for x in json.loads(recorded["rules_json"]))
        assert service.factory.calls[0][2]["approved_style_rules"][0]["statement"] == rule["statement"]
    asyncio.run(scenario())


@pytest.mark.parametrize("output_format,text", [("tiktok", "صيغة خاطئة"), ("x_post", "ن" * 281)])
def test_requested_tweet_format_and_length_are_enforced_atomically(service, output_format, text):
    async def scenario():
        aid = article(service, now())
        payload = await setup(service, include_news=True, article_ids=[aid], format="x_posts")
        service.factory.reply = ChatReply(message="مسودة", drafts=[{"title": "اقتراح", "text": text, "format": output_format, "article_ids": [aid]}])
        job = await finish(service, payload)
        assert job["state"] == "failed" and job["error_code"] == "VALIDATION_ERROR"
        assert service.store.rows("SELECT id FROM drafts") == []
        assert service.store.rows("SELECT id FROM chat_messages WHERE role='assistant'") == []
    asyncio.run(scenario())


def test_foreign_conversation_cannot_be_read_or_used(service):
    async def scenario():
        payload = await setup(service)
        foreign, conversation = uid(), uid()
        with service.db:
            service.db.execute("INSERT INTO workspaces VALUES(?,?,?)", (foreign, "Other", now()))
            service.db.execute("INSERT INTO conversations VALUES(?,?,?,?,?)", (conversation, foreign, "Private", now(), now()))
        with pytest.raises(Failure):
            await service.dispatch("chat.detail", {"conversation_id": conversation})
        with pytest.raises(Failure):
            await service.dispatch("chat.send", {**payload, "conversation_id": conversation})
        assert all(c["id"] != conversation for c in (await service.dispatch("chat.list", {}))["conversations"])
        assert service.factory.calls == []
    asyncio.run(scenario())


def test_resume_requires_new_consent_and_reuses_original_context(service):
    async def scenario():
        aid = article(service, now())
        payload = await setup(service, include_news=True, article_ids=[aid])
        service.factory.release = asyncio.Event()
        job = await service.dispatch("chat.send", payload)
        await service.factory.started.wait()
        await service.dispatch("jobs.cancel", {"job_id": job["job_id"]})
        service.test_articles[aid]["text"] = "محتوى مختلف بعد الإلغاء"
        with pytest.raises(Failure) as denied:
            await service.dispatch("jobs.resume", {"job_id": job["job_id"]})
        assert denied.value.code == "PERMISSION_DENIED"
        service.factory.release = None
        await service.dispatch("jobs.resume", {"job_id": job["job_id"], "consent": True})
        await service.tasks[job["job_id"]]
        assert service.factory.calls[-1][2]["news"][0]["text"] == "مادة الخبر الأصلية"
        assert len(service.store.rows("SELECT id FROM chat_messages WHERE role='user'")) == 1
        assert len(service.store.rows("SELECT id FROM chat_messages WHERE role='assistant'")) == 1
        repeated = await service.dispatch("chat.send", payload)
        assert repeated["job_id"] == job["job_id"] and repeated["state"] == "completed"
    asyncio.run(scenario())


def test_weekly_selection_is_not_limited_by_ui_snapshot_and_deduplicates_urls(service):
    async def scenario():
        current = datetime.now(timezone.utc)
        for index in range(105):
            article(service, None)
        newest = article(service, (current - timedelta(hours=1)).isoformat())
        article(service, (current - timedelta(hours=2)).isoformat(), url=service.test_articles[newest]["url"])
        older = article(service, (current - timedelta(hours=3)).isoformat())
        # Intentionally omit all dated articles from the UI-facing fixture snapshot.
        service.news.snapshot = lambda: {"articles": list(service.test_articles.values())[:100]}
        payload = await setup(service, include_news=True)
        context = service.conversations.source_context(ChatSend.model_validate(payload))
        assert [x["id"] for x in context["news"]] == [newest, older]
    asyncio.run(scenario())


def test_saved_older_story_can_be_found_by_title_when_discussing_news(service):
    async def scenario():
        identifier = article(service, (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                             title="إطلاق قمر بحثي جديد")
        payload = await setup(service, include_news=True, message="اشرح لي إطلاق قمر بحثي جديد")
        context = service.conversations.source_context(ChatSend.model_validate(payload))
        assert [item["id"] for item in context["news"]] == [identifier]
        assert context["news"][0]["text"] == "مادة الخبر الأصلية"
    asyncio.run(scenario())


def test_news_research_is_model_driven_and_keeps_rss_context(service):
    async def scenario():
        aid = article(service, now(), title="ChatGPT feature announcement")
        payload = await setup(service, include_news=True, research_web=True,
                              article_ids=[aid], message="اشرح المقالة وابحث عن خبر سابق مرتبط")
        class ToolModel(FakeChatModel):
            supports_tools = True
            async def run(self, profile, instructions, payload, schema, tools=None, on_turn=None):
                assert {tool.__name__ for tool in tools} == {"search_saved_articles", "read_saved_article", "search_web", "read_web_page", "search_conversation_history"}
                assert "FIRST" in instructions and "explicitly asks" in instructions
                assert payload["news"][0]["id"] == aid
                saved = json.loads(await tools[0]("ChatGPT"))
                assert saved["articles"][0]["id"] == aid
                # The agent decides whether web research is needed; no pre-model RSS web fetch.
                return ChatReply(message="خبر محفوظ", article_ids=[aid])
        service.factory = ToolModel()
        async def forbidden(*args): raise AssertionError("No web request selected")
        service.news.fetch = forbidden
        job = await finish(service, payload)
        assert job["state"] == "completed"
    asyncio.run(scenario())


def test_chat_pagination_is_ordered_bounded_and_rejects_other_conversation_cursor(service):
    async def scenario():
        cid = (await service.dispatch("chat.create", {}))["conversation_id"]
        other = (await service.dispatch("chat.create", {}))["conversation_id"]
        ids = [uid() for _ in range(45)]
        foreign_marker = uid()
        with service.db:
            for index, mid in enumerate(ids):
                service.db.execute("INSERT INTO chat_messages VALUES(?,?,?,?,?,?,?,?,?)", (mid,service.ws,cid,"user",str(index),"[]","[]",None,now()))
            service.db.execute("INSERT INTO chat_messages VALUES(?,?,?,?,?,?,?,?,?)", (foreign_marker,service.ws,other,"user","different conversation","[]","[]",None,now()))
        page1 = await service.dispatch("chat.detail", {"conversation_id":cid})
        assert [m["id"] for m in page1["messages"]] == ids[25:]
        assert page1["has_more"] is True and page1["next_before_message_id"] == ids[25]
        page2 = await service.dispatch("chat.detail", {"conversation_id":cid,"before_message_id":page1["next_before_message_id"]})
        assert [m["id"] for m in page2["messages"]] == ids[5:25]
        page3 = await service.dispatch("chat.detail", {"conversation_id":cid,"before_message_id":page2["next_before_message_id"]})
        assert [m["id"] for m in page3["messages"]] == ids[:5]
        assert page3["has_more"] is False and page3["next_before_message_id"] is None
        with pytest.raises(Failure):
            await service.dispatch("chat.detail", {"conversation_id":cid,"before_message_id":foreign_marker})
    asyncio.run(scenario())


def test_source_preview_is_local_read_only_and_workspace_scoped(service, monkeypatch):
    from eis_engine.news import NewsManager
    monkeypatch.setattr(service.news, "article", NewsManager.article.__get__(service.news))
    identifier = article(service)
    async def scenario():
        preview = await service.dispatch("news.preview", {"article_id": identifier})
        assert preview["text"] == "مادة الخبر الأصلية"
        assert service.db.execute("SELECT is_read FROM news_articles WHERE id=?", (identifier,)).fetchone()[0] == 0
        assert service.factory.calls == []
        other = uid()
        with service.db:
            service.db.execute("INSERT INTO workspaces VALUES(?,?,?)", (other,"Other",now()))
            service.db.execute("UPDATE news_articles SET workspace_id=? WHERE id=?", (other,identifier))
        with pytest.raises(Failure):
            await service.dispatch("news.preview", {"article_id": identifier})
    asyncio.run(scenario())


def test_context_budget_and_history_search_survive_restart_and_isolate_sessions(service):
    from eis_engine.conversation_context import ConversationContext, HISTORY_BYTES
    async def scenario():
        payload = await setup(service)
        cid = payload['conversation_id']
        other = (await service.dispatch('chat.create', {}))['conversation_id']
        ids = [uid() for _ in range(40)]
        with service.db:
            for index, mid in enumerate(ids):
                text = 'اتفقنا على زاوية الطاقة' if index == 0 else ('نقاش طويل ' * 1500)
                service.db.execute('INSERT INTO chat_messages VALUES(?,?,?,?,?,?,?,?,?)', (mid,service.ws,cid,'user',text,'[]','[]',None,now()))
            foreign = uid()
            service.db.execute('INSERT INTO chat_messages VALUES(?,?,?,?,?,?,?,?,?)', (foreign,service.ws,other,'user','زاوية سرية','[]','[]',None,now()))
        context = ConversationContext(service.store, service.ws, cid)
        snapshot = context.snapshot()
        assert snapshot['context_info']['total_messages'] == 40
        assert snapshot['context_info']['has_older_context']
        assert snapshot['context_info']['history_bytes'] <= HISTORY_BYTES
        assert len(snapshot['history']) < 16
        assert context.search('الطاقة')['messages'][0]['id'] == ids[0]
        assert context.search('سرية')['messages'] == []
        assert 'error' in context.search('', foreign)
        with service.db:
            service.db.execute('INSERT INTO chat_messages VALUES(?,?,?,?,?,?,?,?,?)', (uid(),service.ws,cid,'user','رسالة مستقبلية','[]','[]',None,now()))
        # Frozen retry context must not observe turns created after submission.
        assert context.search('مستقبلية')['messages'] == []
        reopened = Store(service.store.path.parent)
        try:
            restored = ConversationContext(reopened, service.ws, cid, snapshot['through'])
            assert restored.search('الطاقة')['messages'][0]['content'] == 'اتفقنا على زاوية الطاقة'
            assert restored.search('مستقبلية')['messages'] == []
        finally: reopened.close()
    asyncio.run(scenario())


def test_session_events_are_scoped_persisted_and_separate_from_answer(service):
    async def scenario():
        payload = await setup(service)
        class EventModel(FakeChatModel):
            supports_tools = True
            supports_session_events = True
            async def run(self, profile, instructions, data, schema, tools=None, on_turn=None,
                          on_reasoning=None, session_id=None, user_id=None, run_id=None):
                if schema.__name__ == 'SummaryPair':
                    return schema(ar='أراجع سياق السؤال. \n\nأربط المصادر المتاحة.', en='I review the question and connect the available sources.')
                assert session_id == payload['conversation_id'] and user_id == service.ws
                assert run_id
                assert 'summaries and progress descriptions must be in Arabic' in instructions
                on_turn()
                on_reasoning('أراجع سياق السؤال. ')
                live = await service.dispatch('chat.progress', {'job_id': run_id})
                assert live['state'] == 'running'
                assert live['execution']['reasoning_summary'] == ''
                assert live['execution']['summary_language'] == 'ar'
                assert live['message'] == ''
                history_tool = next(t for t in tools if t.__name__ == 'search_conversation_history')
                await history_tool('زاوية')
                # A new model turn must not erase past steps or summaries.
                on_turn()
                on_reasoning('أربط المصادر المتاحة.')
                return ChatReply(message='الجواب النهائي')
        service.factory = EventModel()
        job = await finish(service, payload)
        assert job['state'] == 'completed'
        detail = await service.dispatch('chat.detail', {'conversation_id':payload['conversation_id']})
        reply = detail['messages'][-1]
        assert reply['content'] == 'الجواب النهائي'
        assert [s['kind'] for s in reply['activity']['steps']] == ['context','history']
        assert reply['activity']['reasoning_summary'] == 'أراجع سياق السؤال. \n\nأربط المصادر المتاحة.'
        assert reply['activity']['context_info']['total_messages'] == 0
    asyncio.run(scenario())


def test_background_conversation_is_listed_and_finishes_while_another_is_open(service):
    async def scenario():
        payload = await setup(service)
        service.factory.release = asyncio.Event()
        submitted = await service.dispatch('chat.send', payload)
        await service.factory.started.wait()
        second = (await service.dispatch('chat.create', {'title':'Second'}))['conversation_id']
        detail = await service.dispatch('chat.detail', {'conversation_id':second})
        assert detail['active_job_id'] is None
        listing = (await service.dispatch('chat.list', {}))['conversations']
        first = next(row for row in listing if row['id'] == payload['conversation_id'])
        assert first['active_job_id'] == submitted['job_id']
        service.factory.release.set()
        await service.tasks[submitted['job_id']]
        listing = (await service.dispatch('chat.list', {}))['conversations']
        assert all(row['active_job_id'] is None for row in listing)
        restored = await service.dispatch('chat.detail', {'conversation_id':payload['conversation_id']})
        assert restored['messages'][-1]['role'] == 'assistant'
        assert (await service.dispatch('chat.detail', {'conversation_id':second}))['messages'] == []
    asyncio.run(scenario())


def test_month_period_reaches_archive_beyond_initial_source_sample(service):
    async def scenario():
        current = datetime.now(timezone.utc)
        from eis_engine.news_period import resolve_period
        first, last = resolve_period('الشهر الماضي', current.date())
        old = article(service, first.isoformat()+'T12:00:00+00:00')
        for i in range(30):
            article(service, current.isoformat())
        payload = await setup(service, include_news=True, message='أخبار الشهر الماضي')
        context = service.conversations.source_context(ChatSend.model_validate(payload))
        assert [a['id'] for a in context['news']] == [old]
        assert context['window']['requested_dates'] == [first.isoformat(), last.isoformat()]
    asyncio.run(scenario())
