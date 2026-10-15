"""Small public execution record; never provider payloads or hidden reasoning tokens."""
import time


class ConversationActivity:
    def __init__(self, language=None):
        self.language = language
        self.summaries = {}
        self.translated_source = ''
        self.translation_state = 'pending'
        self.translation_updates = []
        self.translation_error = None
        self.started = time.monotonic()
        self.steps = []
        self.reasoning_summary = ''
        self.part_pending = False

    def add(self, kind, detail=''):
        step = {'kind': kind, 'detail': detail[:300], 'elapsed_seconds': int(time.monotonic() - self.started)}
        if self.steps and all(self.steps[-1][key] == step[key] for key in ('kind', 'detail')): return
        if len(self.steps) < 48:
            self.steps.append({'id': str(len(self.steps)), **step})

    def new_reasoning_part(self):
        self.part_pending = bool(self.reasoning_summary)

    def reasoning(self, text):
        if isinstance(text, str) and text:
            if self.part_pending:
                self.reasoning_summary += "\n\n"
                self.part_pending = False
            self.reasoning_summary = (self.reasoning_summary + text)[:16000]

    def snapshot(self):
        return {'steps': list(self.steps),
                'reasoning_summary': self.summaries.get(self.language, '') if self.language else self.reasoning_summary,
                'reasoning_summaries': dict(self.summaries), 'summary_language': self.language,
                'summary_translation_state': self.translation_state,
                'summary_update_seconds': self.translation_updates,
                'summary_translation_error': self.translation_error,
                'elapsed_seconds': int(time.monotonic() - self.started)}
