import asyncio
from eis_engine.activity_translation import ActivityTranslation, SummaryPair
from eis_engine.conversation_activity import ConversationActivity


def test_bilingual_summaries_update_before_finish_and_are_retained():
    async def scenario():
        activity = ConversationActivity('ar')
        started, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def translate(source):
            calls.append(source)
            started.set()
            await release.wait()
            return SummaryPair(ar='أراجع المصادر المتاحة وأقارن المعلومات.', en='I review the available sources and compare information.')
        worker = ActivityTranslation(activity, translate)
        activity.reasoning('Reviewing sources')
        worker.notify()
        await started.wait()
        assert activity.snapshot()['reasoning_summary'] == ''
        assert activity.translation_state == 'translating'
        release.set()
        for _ in range(100):
            if activity.translation_state == 'ready': break
            await asyncio.sleep(.01)
        assert not worker.task.done()  # Ready while generation is still running.
        assert activity.snapshot()['reasoning_summary'].startswith('أراجع')
        assert set(activity.snapshot()['reasoning_summaries']) == {'ar', 'en'}
        activity.language = 'en'
        assert activity.snapshot()['reasoning_summary'].startswith('I review')
        await worker.finish()
        assert len(calls) == 1
    asyncio.run(scenario())


def test_translation_failure_never_substitutes_wrong_language():
    async def scenario():
        activity = ConversationActivity('ar')
        async def fail(source): raise RuntimeError('offline')
        worker = ActivityTranslation(activity, fail)
        activity.reasoning('Reading sources')
        worker.notify()
        await worker.finish()
        assert activity.snapshot()['reasoning_summary'] == ''
        assert activity.translation_state == 'unavailable'
    asyncio.run(scenario())
