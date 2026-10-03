"""Two simple, visible checks on the report text itself. Neither sets a severity by reading meaning.

  * Does the text look like instructions aimed at the reader? (a short phrase list in data/reference/)
  * Is the report very short? (then details are probably missing)
"""
import re
from dataclasses import dataclass

SHORT_REPORT_WORDS = 8


@dataclass(frozen=True)
class TextRead:
    instruction_like: bool
    word_count: int

    @property
    def very_short(self) -> bool:
        return self.word_count < SHORT_REPORT_WORDS


def read_text(text: str, instruction_phrases: list[str]) -> TextRead:
    body = re.sub(r"\s+", " ", text.lower().replace("’", "'").replace("‘", "'"))
    return TextRead(
        instruction_like=any(p in body for p in instruction_phrases),
        word_count=len(re.findall(r"[A-Za-z0-9']+", text)),
    )
