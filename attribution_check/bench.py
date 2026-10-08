"""Load the labeled meetings and score the checker."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .core import Segment, Verdict, check


def load(path: Path) -> tuple[dict, list[Segment]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    segs = [Segment(i, s["speaker"], s["start"], s["text"]) for i, s in enumerate(doc["segments"])]
    return doc, segs


def expected(label: str) -> tuple[str, str | None]:
    if label == "ok":
        return "SUPPORTED", None
    if label == "unsupported":
        return "UNSUPPORTED", None
    return "MISATTRIBUTED", label.split(":", 1)[1]


@dataclass
class Score:
    lines: int = 0
    planted: int = 0
    caught: int = 0              # right label (and right speaker for misattributions)
    false_alarms: int = 0        # correct line flagged as wrong
    misses: list[str] = field(default_factory=list)

    @property
    def recall(self) -> float:
        return self.caught / self.planted if self.planted else 1.0


def score_meeting(doc: dict, verdicts: list[Verdict], sc: Score) -> None:
    for v in verdicts:
        label = doc["labels"].get(str(v.claim.line_no))
        if label is None:
            continue
        sc.lines += 1
        want, who = expected(label)
        if label == "ok":
            if v.label != "SUPPORTED":
                sc.false_alarms += 1
                sc.misses.append(f"{doc['id']}: false alarm on '{v.claim.text}' ({v.label})")
            continue
        sc.planted += 1
        if v.label == want and (who is None or v.correct == who):
            sc.caught += 1
        else:
            sc.misses.append(f"{doc['id']}: missed '{v.claim.text}' (got {v.label}/{v.correct}, want {want}/{who})")


def run(folder: Path):
    sc, results = Score(), []
    for p in sorted(folder.glob("*.json")):
        doc, segs = load(p)
        verdicts = check(segs, doc["summary"])
        score_meeting(doc, verdicts, sc)
        results.append((doc, segs, verdicts))
    return sc, results
