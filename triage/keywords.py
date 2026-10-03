"""The code's own simple read of a report, using the visible keyword table. No AI involved.

It can only ever RAISE a priority (through a floor). It never lowers anything.
Known limit: plain word matching over-triggers ("no injuries" contains "injur"). That is accepted.
"""
import re
from dataclasses import dataclass

from triage.reference import Keyword

SHORT_REPORT_WORDS = 8


@dataclass(frozen=True)
class GroupHit:
    group: str
    floor: int
    reason: str
    words: tuple[str, ...]      # the keywords that matched, in table order


@dataclass(frozen=True)
class CodeRead:
    floor: int                      # highest floor among the matched groups, 0 if none
    hits: tuple[GroupHit, ...]      # matched groups, highest floor first
    injury_words: bool              # any injury words were found (these are often negated, e.g. "no injuries")
    serious_injury_words: bool      # words that suggest a serious injury (ambulance, hospital, ...)
    damage_words: bool              # aircraft damage words were found
    instruction_like: bool          # text that looks like instructions aimed at the reader
    word_count: int

    @property
    def very_short(self) -> bool:
        return self.word_count < SHORT_REPORT_WORDS

    @property
    def top_hit(self) -> GroupHit | None:
        return self.hits[0] if self.hits else None


def _normalise(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text)


def read_report(text: str, keywords: list[Keyword], instruction_phrases: list[str]) -> CodeRead:
    body = _normalise(text)
    by_group: dict[str, list[tuple[Keyword, str]]] = {}
    for k in keywords:
        # show the word as written in the report ("injuries"), not the search stem ("injur")
        found = re.search(r"[\w']*" + re.escape(k.keyword) + r"[\w']*", body)
        if found:
            by_group.setdefault(k.group, []).append((k, found.group(0)))
    hits = sorted(
        (GroupHit(group, pairs[0][0].floor, pairs[0][0].reason, tuple(dict.fromkeys(shown for _, shown in pairs)))
         for group, pairs in by_group.items()),
        key=lambda h: (-h.floor, h.group),
    )
    groups = {h.group for h in hits}
    return CodeRead(
        floor=max((h.floor for h in hits), default=0),
        hits=tuple(hits),
        injury_words=bool(groups & {"injury", "serious_injury"}),
        serious_injury_words="serious_injury" in groups,
        damage_words="aircraft_damage" in groups,
        instruction_like=any(p in body for p in instruction_phrases),
        word_count=len(re.findall(r"[A-Za-z0-9']+", text)),
    )
