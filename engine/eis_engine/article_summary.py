"""Explicit article summaries through the existing Agno model route."""
import asyncio
import time
from pydantic import BaseModel, Field
from .contracts import Failure
from .storage import digest, encode


class SummaryQuote(BaseModel):
    source_id: str = Field(max_length=12)
    text: str = Field(min_length=1, max_length=600)


class ArticleSummary(BaseModel):
    summary: str = Field(min_length=1, max_length=12000)
    quotes: list[SummaryQuote] = Field(default_factory=list, max_length=8)


class SummaryPoint(BaseModel):
    text: str = Field(min_length=1,max_length=500)
    source_ids: list[str] = Field(min_length=1,max_length=4)


class ArticleTLDR(ArticleSummary):
    key_points: list[SummaryPoint] = Field(min_length=1,max_length=3)
    sequence: list[SummaryPoint] = Field(max_length=3)
    viewpoints: list[SummaryPoint] = Field(max_length=3)
    uncertainties: list[SummaryPoint] = Field(max_length=2)
    quotes: list[SummaryQuote] = Field(default_factory=list,max_length=2)


async def summarize(service, params):
    if params.get("consent") is not True:
        raise Failure("PERMISSION_DENIED", "فعّل استخدام النماذج من إعدادات الصلاحيات للمتابعة.")
    language = params.get("language", service.news_digest.settings()["language"])
    if language not in {"ar", "en"}:
        raise Failure("VALIDATION_ERROR", "لغة غير صالحة.")
    article = service.news.article(params.get("article_id"), mark_read=False)
    regenerate = params.get('regenerate') is True
    prepared = service.news_digest.preview(article["id"], language)
    if prepared and not prepared.get('needs_refresh') and not regenerate:
        return prepared
    evidence = article["text"] or article["summary"]
    if not evidence.strip():
        raise Failure("VALIDATION_ERROR", "لا يتوفر نص لتلخيصه.")
    assignment = service.news_digest.assignment()
    if not assignment:
        assignment = service.store.one("SELECT profile_id,model_id FROM agent_assignments WHERE workspace_id=? AND role='writer'", (service.ws,))
    if not assignment:
        raise Failure("VALIDATION_ERROR", "اختر اتصالًا ونموذجًا للكاتب من الإعدادات أولًا.")
    if assignment['profile_id']=='local-summary':
        profile = {'id':'local-summary'}
    else:
        profile = service.profile(assignment["profile_id"])
        service.validate_model(profile["id"], assignment["model_id"])
    profile["model_id"] = assignment["model_id"]
    from .news_digest_cache import fingerprint
    from .editorial_instructions import load
    instructions = load(service.store, 'article-summary')
    signature = digest(encode([fingerprint(article),language,assignment,instructions,'tldr-4']))
    service.db.execute('CREATE TABLE IF NOT EXISTS article_tldr_manual(workspace_id TEXT,signature TEXT,payload TEXT,PRIMARY KEY(workspace_id,signature))')
    cached = service.store.one('SELECT payload FROM article_tldr_manual WHERE workspace_id=? AND signature=?',(service.ws,signature))
    if cached and not regenerate:
        import json
        return {**json.loads(cached['payload']),'cached':True}
    digest_service = service.news_digest
    if digest_service.manual_pending:
        raise Failure('BUSY', 'يجري تجهيز ملخص حسب الطلب. انتظر اكتماله ثم أعد المحاولة.')
    if profile['id'] != 'local-summary' or digest_service.budget.phase() != 'resting':
        digest_service.evidence.check_budget(profile)
    digest_service.manual_pending = True
    started = time.monotonic()
    try:
        pending = digest_service.active_request
        if pending:
            # Explicit reader work takes priority, after bounded runner cleanup.
            # Completed long-article notes let background work resume later.
            digest_service.interrupt_for_user()
            try: await asyncio.shield(pending)
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling(): raise
            except Exception: pass
        while profile['id']=='local-summary' and digest_service.budget.phase()=='resting':
            await asyncio.sleep(min(.25,max(.01,digest_service.budget.next_at-time.monotonic())))
        if service.model_lock.locked():
            raise Failure('BUSY', 'انتظر اكتمال الطلب الحالي ثم أعد المحاولة.')
        result = await digest_service.evidence.prepare(profile,article,language,
            instructions,ArticleSummary,regenerate=regenerate)
        # Preserve the prior summary until the replacement has passed validation.
        digest_service.cache.save(article, language, assignment, result['summary'], evidence=result)
        saved = service.store.one('SELECT updated_at FROM news_digest_results WHERE workspace_id=? AND article_id=?', (service.ws, article['id']))
        result = {**result, 'generated_at':saved['updated_at']}
        with service.db:
            service.db.execute('INSERT OR REPLACE INTO article_tldr_manual VALUES(?,?,?)',(service.ws,signature,encode({**result,'model':profile['model_id']})))
        return {**result,'model':profile['model_id'],'cached':False}
    finally:
        if profile['id']=='local-summary': digest_service.budget.finished(time.monotonic()-started)
        digest_service.manual_pending = False
