"""Bounded, coalesced translation of provider-visible summaries, never hidden reasoning."""
import asyncio
import time
import re
from pydantic import BaseModel, Field


class SummaryPair(BaseModel):
    ar: str = Field(max_length=20000)
    en: str = Field(max_length=20000)


class ActivityTranslation:
    def __init__(self, activity, translate):
        self.activity, self.translate = activity, translate
        self.changed = asyncio.Event()
        self.stopping = False
        self.task = asyncio.create_task(self.work())

    def notify(self):
        self.changed.set()

    async def work(self):
        while True:
            await self.changed.wait()
            self.changed.clear()
            if not self.stopping:
                await asyncio.sleep(0.5)  # Coalesce token deltas, not one request per token.
                self.changed.clear()
            source = self.activity.reasoning_summary.strip()
            if source and source != self.activity.translated_source:
                self.activity.translation_state = 'translating'
                try:
                    pair = SummaryPair.model_validate(await asyncio.wait_for(self.translate(source), 20))
                    if not re.search(r'[\u0621-\u064a\u066e-\u06d3]', pair.ar) or not re.search(r'[A-Za-z]', pair.en):
                        raise ValueError('Translation language mismatch')
                    self.activity.summaries = {'ar': pair.ar.strip(), 'en': pair.en.strip()}
                    self.activity.translated_source = source
                    self.activity.translation_state = 'ready'
                    self.activity.translation_updates.append(int(time.monotonic() - self.activity.started))
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    self.activity.translation_error = type(error).__name__
                    self.activity.translation_state = 'unavailable'
            if self.activity.reasoning_summary.strip() != source:
                self.changed.set()
            elif self.stopping:
                return

    async def finish(self):
        self.stopping = True
        self.changed.set()
        try:
            await asyncio.wait_for(self.task, 25)
        except TimeoutError:
            self.activity.translation_state = 'unavailable'
        finally:
            if not self.task.done():
                self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
