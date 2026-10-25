"""TL;DR evidence, resume, attribution and resource contracts; no live network/models."""
import asyncio
import pytest
from eis_engine.article_summary import ArticleSummary, summarize
from eis_engine.summary_evidence import links_in
from eis_engine.contracts import Failure
from test_news_digest import service


async def configure(service, local=False):
    if local:
        service.news_digest.local.installed={'writer:small':100}
        service.news_digest.configure({'enabled':True,'engine':'local','local_model':'writer:small','language':'en'})
        service.news_digest.device_state({'thermal':'nominal','low_power':False,'memory_pressure':'normal','on_battery':False})
    else:
        saved=await service.dispatch('providers.save',{'provider_key':'openai','model_id':'economy'})
        from eis_engine.storage import encode, now
        with service.db:
            service.db.execute('INSERT INTO model_catalogs VALUES(?,?,?,?,?,?,?)',(saved['profile_id'],service.ws,encode([{'id':'economy','available':True}]),'fixture',now(),None,9999999999))
        await service.dispatch('agents.assign',{'role':'news','profile_id':saved['profile_id'],'model_id':'economy'})
        service.news_digest.configure({'enabled':True,'language':'en'})


def test_links_are_editorial_deduplicated_and_one_hop():
    assert links_in('[report](/report#one) [same](/report#two) https://other.example/news. ![pic](/pic.png) [bad](javascript:alert)', 'https://publisher.example/story') == ['https://publisher.example/report','https://other.example/news']


def test_background_tldr_follows_links_caches_and_verifies_quotes(service):
    async def run():
        await configure(service)
        body='The minister said the proposal remains under review. '+('There is more context about the negotiations. '*8)
        with service.db:
            service.db.execute("UPDATE news_articles SET text=? WHERE id='story'",('A report discusses competing positions. [Report](https://other.example/report) [Tweet](https://x.com/a/status/1) '+('Context. '*30),))
        fetched=[]
        async def fetch(url,_):
            fetched.append(url)
            if 'x.com' in url: raise OSError('requires login')
            return {'url':url,'headers':{'content-type':'text/html'},'body':('<article><p>'+body+'</p><a href="https://nested.example/never">Nested</a></article>').encode()}
        service.news.fetch=fetch
        calls=[]
        async def model(profile,instructions,data,schema):
            calls.append(data)
            return ArticleSummary(summary='The proposal remains under review [S2]. Invalid [S99]. [Fake](https://made-up.example/)',quotes=[
                {'source_id':'S2','text':'the proposal remains under review.'},
                {'source_id':'S2','text':'An invented quotation.'},
                {'source_id':'S3','text':'Text from a blocked source.'}])
        service.factory.run=model
        assert await service.news_digest.prepare_next()
        result=service.news_digest.preview('story','en')
        assert 'https://other.example/report' in result['summary']
        assert 'https://made-up.example/' not in result['summary'] and '[S99]' not in result['summary']
        assert len(result['quotes'])==1
        assert [s['status'] for s in result['sources']]==['read','read','unavailable']
        assert len(fetched)==2 and len(calls)==1
        assert not await service.news_digest.prepare_next()
        assert (await summarize(service,{'article_id':'story','consent':True}))['sources']==result['sources']
        with service.db: service.db.execute("UPDATE news_articles SET title='Correction' WHERE id='story'")
        assert await service.news_digest.prepare_next()
        assert len(fetched)==2  # Cached evidence, including inaccessible links.
    asyncio.run(run())


def test_first_hop_limit_is_visible_and_has_no_recursive_fetch(service):
    async def run():
        await configure(service)
        text='A long report with references. '*5+' '.join(f'[Source {i}](https://source.example/{i})' for i in range(9))
        with service.db: service.db.execute("UPDATE news_articles SET text=? WHERE id='story'",(text,))
        fetched=[]
        async def fetch(url,_):
            fetched.append(url)
            return {'url':url,'headers':{'content-type':'text/html'},'body':b'<article><p>Public evidence and detailed context about the reported event. Multiple positions are discussed with care.</p><p><a href="https://nested.example/never">Nested source</a></p></article>'}
        service.news.fetch=fetch
        assert await service.news_digest.prepare_next()
        result=service.news_digest.preview('story','en')
        assert len(fetched)==6 and result['coverage']['unvisited_links']==3
        assert len(result['sources'])==7
    asyncio.run(run())


def test_long_article_notes_resume_after_cancellation_and_include_the_end(service):
    async def run():
        await configure(service)
        text=('Opening details. '*600)+('Middle facts. '*600)+'The final paragraph contains a correction.'
        with service.db: service.db.execute("UPDATE news_articles SET text=? WHERE id='story'",(text,))
        parts=[]
        fail=True
        async def model(profile,instructions,data,schema):
            nonlocal fail
            if data.get('note_pass'):
                if fail and parts: raise asyncio.CancelledError()
                parts.append(data['sources'][0]['text'])
                return ArticleSummary(summary='Factual section notes preserving the reported details.')
            return ArticleSummary(summary='A combined summary retaining the correction and uncertainty [S1].')
        service.factory.run=model
        assert not await service.news_digest.prepare_next()
        assert len(parts)==1
        fail=False
        assert await service.news_digest.prepare_next()
        assert len(parts)==(len(text)+4499)//4500
        assert 'correction' in parts[-1]
        assert service.news_digest.preview('story','en')['coverage']['limited'] is False
    asyncio.run(run())


@pytest.mark.parametrize('state',['memory_pressure','cooling','waiting_device','paused'])
def test_no_network_or_inference_under_resource_block(service,state):
    async def run():
        await configure(service,local=True)
        budget=service.news_digest.budget
        if state=='memory_pressure': budget.memory_pressure='warning'
        elif state=='cooling': budget.thermal='fair'
        elif state=='waiting_device': budget.updated=0
        else: budget.paused=True
        async def forbidden(*args): pytest.fail('Work must not start while blocked')
        service.news.fetch=forbidden; service.news_digest.local.run=forbidden
        assert not await service.news_digest.prepare_next()
        with pytest.raises(Failure) as error:
            await summarize(service,{'article_id':'story','consent':True})
        assert error.value.code=='RESOURCE_WAIT'
    asyncio.run(run())


def test_structured_summary_renders_positions_and_only_known_citations(service):
    from eis_engine.article_summary import ArticleTLDR
    async def run():
        await configure(service)
        async def model(profile,instructions,data,schema):
            assert schema is ArticleTLDR
            return ArticleTLDR(summary='A city proposes a new park.',key_points=[{'text':'The budget is provisional.','source_ids':['S1']}],sequence=[{'text':'Construction would start in March.','source_ids':['S1']}],viewpoints=[{'text':'Residents welcome greenery; shopkeepers oppose the road closure.','source_ids':['S1']}],uncertainties=[{'text':'A traffic plan is not announced.','source_ids':['S1']},{'text':'Unsupported claim.','source_ids':['S99']}])
        service.factory.run=model
        assert await service.news_digest.prepare_next()
        summary=service.news_digest.preview('story','en')['summary']
        assert '### Key facts' in summary and '### Sequence' in summary
        assert '### Perspectives' in summary and '### Uncertainty' in summary
        assert 'shopkeepers' in summary and 'Unsupported' not in summary
    asyncio.run(run())


def test_quote_matching_does_not_cut_an_arabic_word_and_change_tense(service):
    async def run():
        await configure(service)
        with service.db: service.db.execute("UPDATE news_articles SET text=? WHERE id='story'",('يبدأ التنفيذ في مارس 2027. '+('تفاصيل موثقة في المقال. '*8),))
        async def model(*args):
            return ArticleSummary(summary='Construction is planned for March 2027.',quotes=[{'source_id':'S1','text':'بدأ التنفيذ في مارس 2027.'}])
        service.factory.run=model
        assert await service.news_digest.prepare_next()
        assert service.news_digest.preview('story','en')['quotes']==[]
    asyncio.run(run())


def test_unsupported_figures_get_one_repair_then_fail_closed(service):
    from eis_engine.article_summary import ArticleTLDR
    async def run():
        await configure(service)
        with service.db: service.db.execute("UPDATE news_articles SET text=? WHERE id='story'",('Budget: two million for trees, three million for paths. '+('Additional context. '*8),))
        calls=[]
        async def model(profile,instructions,data,schema):
            calls.append(data)
            return ArticleTLDR(summary='The budget remains provisional.',key_points=[{'text':'Trees cost 1 million.','source_ids':['S1']}],sequence=[],viewpoints=[],uncertainties=[])
        service.factory.run=model
        assert await service.news_digest.prepare_next()
        assert len(calls)==2 and 'correction_required' in calls[1]
        assert service.news_digest.preview('story','en') is None
    asyncio.run(run())


def test_short_complete_news_enters_the_queue_with_publication_context(service):
    async def run():
        await configure(service)
        with service.db:
            service.db.execute("UPDATE news_articles SET text='The council approved the plan.',published_at='2026-10-25T08:00:00Z' WHERE id='story'")
        assert service.news_digest.status()['pending']==1
        seen=[]
        async def model(profile,instructions,data,schema):
            seen.append(data)
            return ArticleSummary(summary='The council approved the proposed plan.')
        service.factory.run=model
        assert await service.news_digest.prepare_next()
        assert seen[0]['published_at']=='2026-10-25T08:00:00Z'
        assert service.news_digest.preview('story','en')
    asyncio.run(run())


def test_legacy_saved_summary_is_reconciled_once_without_regeneration(service):
    from eis_engine.storage import digest,encode
    from eis_engine.news_digest import NewsDigest
    async def run():
        await configure(service)
        article=service.news.article('story',mark_read=False)
        assignment=service.news_digest.assignment()
        service.news_digest.cache.save(article,'en',assignment,'A previously saved explanation.')
        old_hash=digest('explanation-3:'+encode({k:article.get(k) for k in ('title','url','published_at','text','body_status')}))
        with service.db:
            service.db.execute("UPDATE news_digest_results SET source_hash=?,source_revision=0 WHERE article_id='story'",(old_hash,))
            # Simulate a workspace written before the reconciliation migration.
            service.db.execute('DROP TABLE news_digest_cache_migrations')
        before=service.store.one("SELECT summary,model_id,updated_at FROM news_digest_results WHERE article_id='story'")
        service.news_digest=NewsDigest(service)
        result=service.news_digest.preview('story','en')
        assert result['summary']==before['summary'] and result['model']==before['model_id']
        assert result['generated_at']==before['updated_at'] and result['coverage']['limited']
        assert not result.get('needs_refresh')
        assert service.news_digest.status()['prepared']==1 and service.news_digest.status()['pending']==0
        assert service.news_digest.article_states(['story'])['states']['story']=='ready'
        assert not await service.news_digest.prepare_next() and service.factory.calls==[]
        # Reopening and changing the future generating model do not discard it.
        service.news_digest=NewsDigest(service)
        with service.db: service.db.execute("UPDATE agent_assignments SET model_id='new-model' WHERE role='news'")
        assert service.news_digest.preview('story','en')['model']==before['model_id']
        assert service.news_digest.status()['prepared']==1
        assert not await service.news_digest.prepare_next() and service.factory.calls==[]
        with service.db:
            service.db.execute('UPDATE model_catalogs SET models_json=? WHERE profile_id=?',
                (encode([{'id':'new-model','available':True}]),assignment['profile_id']))
        replacement=await summarize(service,{'article_id':'story','consent':True,'regenerate':True})
        assert replacement['model']=='new-model' and len(service.factory.calls)==1
        with service.db: service.db.execute("UPDATE news_articles SET text=text||' Changed text.' WHERE id='story'")
        assert service.news_digest.preview('story','en') is None
        assert service.news_digest.article_states(['story'])['states']['story']=='outdated'
        assert service.news_digest.status()['prepared']==0
    asyncio.run(run())


def test_reconciliation_restores_retained_prose_without_inventing_its_creation_time(service):
    from eis_engine.news_digest import NewsDigest
    from eis_engine.news_digest_cache import fingerprint
    from eis_engine.storage import encode
    async def run():
        await configure(service)
        article=service.news.article('story',mark_read=False)
        service.news_digest.cache.save(article,'en',service.news_digest.assignment(),evidence={
            'legacy_summary':'A saved summary retained during an earlier failed upgrade.',
            'legacy_hash':fingerprint(article),
        })
        with service.db: service.db.execute('DROP TABLE news_digest_cache_migrations')
        service.news_digest=NewsDigest(service)
        result=service.news_digest.preview('story','en')
        assert result['summary'].startswith('A saved summary retained')
        assert result['generated_at'] is None and not result.get('needs_refresh')
        assert service.news_digest.status()['prepared']==1
        assert not await service.news_digest.prepare_next() and service.factory.calls==[]
    asyncio.run(run())


@pytest.mark.parametrize('change', ['source', 'language'])
def test_reconciliation_rejects_changed_sources_and_wrong_language(service,change):
    from eis_engine.storage import digest,encode
    from eis_engine.news_digest import NewsDigest
    async def run():
        await configure(service)
        article=service.news.article('story',mark_read=False)
        service.news_digest.cache.save(article,'en',service.news_digest.assignment(),'A previously saved explanation.')
        old_hash=digest('explanation-3:'+encode({k:article.get(k) for k in ('title','url','published_at','text','body_status')}))
        with service.db:
            service.db.execute("UPDATE news_digest_results SET source_hash=?,source_revision=0 WHERE article_id='story'",(old_hash,))
            service.db.execute('DROP TABLE news_digest_cache_migrations')
            if change=='source': service.db.execute("UPDATE news_articles SET text=text||' A new fact.' WHERE id='story'")
            else: service.db.execute("UPDATE news_digest_results SET summary='هذا ملخص عربي محفوظ بلغة مختلفة عن اللغة المطلوبة.' WHERE article_id='story'")
        service.news_digest=NewsDigest(service)
        assert service.news_digest.preview('story','en') is None
        assert service.news_digest.status()['prepared']==0
        assert service.news_digest.cache.candidate('en',service.news_digest.assignment(),0)
        assert service.factory.calls==[]
    asyncio.run(run())


def test_explicit_regeneration_bypasses_both_summary_caches_and_keeps_the_replacement(service):
    async def run():
        await configure(service)
        initial=await summarize(service,{'article_id':'story','consent':True})
        before=len(service.factory.calls)
        assert (await summarize(service,{'article_id':'story','consent':True}))['cached']
        assert len(service.factory.calls)==before
        async def changed(profile,instructions,data,schema):
            service.factory.calls.append((profile['model_id'],data['title']))
            return ArticleSummary(summary='A newly regenerated summary with the original factual context.')
        service.factory.run=changed
        new=await summarize(service,{'article_id':'story','consent':True,'regenerate':True})
        assert new['summary']!=initial['summary'] and new['cached'] is False
        assert len(service.factory.calls)==before+1 and new['model']=='economy'
        assert new['generated_at']
        assert service.news_digest.preview('story','en')['summary']==new['summary']
        assert (await summarize(service,{'article_id':'story','consent':True}))['summary']==new['summary']
        assert len(service.factory.calls)==before+1 and not service.news_digest.manual_pending
    asyncio.run(run())


def test_failed_regeneration_retains_the_previous_summary_and_releases_priority(service):
    async def run():
        await configure(service)
        original=await summarize(service,{'article_id':'story','consent':True})
        async def failed(*_): raise RuntimeError('Synthetic provider failure')
        service.factory.run=failed
        with pytest.raises(RuntimeError):
            await summarize(service,{'article_id':'story','consent':True,'regenerate':True})
        assert service.news_digest.preview('story','en')['summary']==original['summary']
        assert not service.news_digest.manual_pending
    asyncio.run(run())


def test_manual_regeneration_safely_interrupts_background_and_blocks_duplicate_requests(service):
    async def run():
        await configure(service)
        await summarize(service,{'article_id':'story','consent':True})
        pending=asyncio.create_task(asyncio.sleep(30))
        service.news_digest.active_request=pending
        started,finish=asyncio.Event(),asyncio.Event()
        async def changed(profile,instructions,data,schema):
            started.set();await finish.wait()
            return ArticleSummary(summary='A regenerated summary after the background request stopped.')
        service.factory.run=changed
        request=asyncio.create_task(summarize(service,{'article_id':'story','consent':True,'regenerate':True}))
        await started.wait()
        assert pending.cancelled() and service.news_digest.manual_pending
        assert await service.news_digest.prepare_next() is False
        with pytest.raises(Failure) as failure:
            await summarize(service,{'article_id':'story','consent':True,'regenerate':True})
        assert failure.value.code=='BUSY'
        finish.set();assert (await request)['cached'] is False
        assert not service.news_digest.manual_pending
        service.news_digest.active_request=None
    asyncio.run(run())


def test_local_regeneration_waits_for_short_duty_cycle_rest_without_starting_background(service):
    async def run():
        import time
        await configure(service,local=True)
        budget=service.news_digest.budget
        budget.next_at=time.monotonic()+.03
        calls=[]
        async def model(name,instructions,data,schema):
            assert service.news_digest.manual_pending
            assert not await service.news.knowledge.embed_next()
            calls.append(name)
            return ArticleSummary(summary='A regenerated local summary with the original factual context.')
        service.news_digest.local.run=model
        start=time.monotonic()
        result=await summarize(service,{'article_id':'story','consent':True,'regenerate':True})
        assert time.monotonic()-start>=.03 and calls==['writer:small']
        assert result['cached'] is False and not service.news_digest.manual_pending
        assert budget.phase()=='resting'
    asyncio.run(run())
