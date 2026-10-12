"""Extract only the user-facing message from an incomplete structured response."""
from pydantic_core import from_json
from .contracts import Failure

class MessagePreview:
    def __init__(self):
        self.buffer = ""
        self.message = ""

    def append(self, delta):
        if not isinstance(delta,str): return self.message
        if len(self.buffer) + len(delta) > 1_000_000:
            raise Failure("MODEL_RESPONSE_INVALID", "تجاوز الرد الحجم المسموح.")
        self.buffer += delta
        source = self.buffer.lstrip()
        if source.startswith("```json"): source = source[7:].lstrip()
        elif source.startswith("```"): source = source[3:].lstrip()
        try:
            parsed = from_json(source,allow_partial="trailing-strings")
            message = parsed.get("message") if isinstance(parsed,dict) else None
            if isinstance(message,str):
                # Do not expose half a UTF-16 surrogate from an escaped JSON character.
                self.message = "".join(c for c in message[:18000] if not 0xD800 <= ord(c) <= 0xDFFF)
        except ValueError:
            pass
        return self.message
