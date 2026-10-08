"""Check who-said / who-will-do claims in a meeting summary against the speaker-tagged transcript.

Pipeline: summary bullets -> claims (named person, kind, content tokens)
          transcript -> evidence units (single lines + accepted hand-offs) with an owner
          claim vs units -> SUPPORTED / MISATTRIBUTED (+ right speaker) / UNSUPPORTED
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------- text

STOP = set("""
a an the and or but of to in on at for with by from as is are was were be been being it its this that these those
i you he she we they me him her us them my your his our their mine yours
will would shall should can could may might must do does did done have has had get got go going gonna
so just also then than there here what which who whom when where why how if not no yes yeah yep ok okay sure
um uh like really very quite about over into up out down off again more most some any all both each every
let lets let's think know want wants need needs said says say asked asks suggested suggests reported reports
described describes noted notes mentioned mentions agreed agrees told tells thanks thank great good right
""".split())
CONTRACTIONS = {"i'll": "i will", "we'll": "we will", "you'll": "you will", "i'd": "i would", "i've": "i have",
                "won't": "will not", "can't": "can not", "let's": "let us", "that's": "that is", "it's": "it is"}


def stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokens(text: str, drop: set[str] = frozenset()) -> set[str]:
    t = text.lower().replace("’", "'")
    for k, v in CONTRACTIONS.items():
        t = t.replace(k, v)
    out = set()
    for w in re.findall(r"[a-z0-9]+", t):
        if w in STOP or w in drop or (len(w) < 2 and not w.isdigit()):
            continue
        out.add(stem(w))
    return out


def mmss(seconds: float) -> str:
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


# ---------------------------------------------------------------- transcript side

@dataclass
class Segment:
    idx: int
    speaker: str
    start: float
    text: str


@dataclass
class Unit:
    """A piece of transcript evidence and who it belongs to."""
    seg_ids: list[int]
    speaker: str          # who said it (for 'X said ...' claims)
    owner: str            # who owns any commitment in it (for 'X will ...' claims)
    toks: set[str]
    start: float
    handoff: bool = False


REQUEST = re.compile(r"\b(can|could|would|will) you\b|\bplease\b", re.I)
AFFIRM = re.compile(r"^\s*(sure|yes|yep|yeah|ok|okay|will do|on it|absolutely|of course|no problem|happy to)\b", re.I)


def build_units(segs: list[Segment], names: set[str]) -> list[Unit]:
    drop = {n.lower() for n in names}
    units: list[Unit] = []
    owner = {s.idx: s.speaker for s in segs}
    for i, s in enumerate(segs):
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        if not (REQUEST.search(s.text) and nxt and nxt.speaker != s.speaker and AFFIRM.search(nxt.text)):
            continue
        # Who is being asked: the vocative ("Dev, can you ...") — not any name mentioned ("send Tom the report").
        m = re.match(r"^\s*([A-Z]\w+),", s.text) or re.search(r"\b([A-Z]\w+), (?:can|could|would|will|please)\b", s.text)
        addressed = m.group(1) if m and m.group(1) in names else None
        if addressed and addressed != nxt.speaker:
            continue
        # "Dev, can you send the report?" -> "Sure" : Dev owns the task, even though Priya said the words.
        owner[s.idx] = nxt.speaker
        units.append(Unit([s.idx, nxt.idx], s.speaker, nxt.speaker,
                          tokens(s.text, drop) | tokens(nxt.text, drop), s.start, handoff=True))
    for s in segs:
        units.append(Unit([s.idx], s.speaker, owner[s.idx], tokens(s.text, drop), s.start))
    return units


# ---------------------------------------------------------------- summary side

COMMIT = re.compile(r"\b(will|'ll|is going to|agreed to|committed to|promised to|offered to|owns|is responsible for)\b", re.I)
NOT_PEOPLE = {"The", "We", "Team", "Both", "Everyone", "Next", "Action", "Summary", "They", "It", "This", "All"}


@dataclass
class Claim:
    line_no: int
    text: str
    person: str | None
    kind: str             # "statement" | "commitment"
    toks: set[str] = field(default_factory=set)


def parse_summary(summary: str, speakers: set[str]) -> list[Claim]:
    claims, section = [], ""
    for n, raw in enumerate(summary.splitlines()):
        line = raw.strip()
        if line.startswith("#"):
            section = line.lower()
            continue
        if not line.startswith(("- ", "* ")):
            continue
        body = line[2:].strip()
        person, kind = None, "statement"
        if m := re.match(r"^([A-Z][a-z]+):\s*(.+)$", body):                      # "Mark: book the hall"
            person, kind = m.group(1), "commitment"
        elif m := re.search(r"\b([A-Z][a-z]+) asked ([A-Z][a-z]+) to\b", body):   # "Priya asked Dev to send ..."
            person, kind = m.group(2), "commitment"
        else:
            first = re.match(r"^([A-Z][a-z]+)\b", body)
            if first and first.group(1) not in NOT_PEOPLE:
                person = first.group(1)
            else:
                person = next((s for s in speakers if re.search(rf"\b{s}\b", body)), None)
            if COMMIT.search(body) or "action" in section:
                kind = "commitment"
        drop = {s.lower() for s in speakers} | ({person.lower()} if person else set())
        claims.append(Claim(n, line, person, kind, tokens(body, drop)))
    return claims


# ---------------------------------------------------------------- verdicts

SUPPORT_MIN = 0.6     # share of the claim's content words found in one evidence unit
TIE = 0.05


@dataclass
class Verdict:
    claim: Claim
    label: str                        # SUPPORTED | MISATTRIBUTED | UNSUPPORTED | NO_SPEAKER
    correct: str | None = None
    evidence: Unit | None = None
    coverage: float = 0.0
    note: str = ""


def check(segs: list[Segment], summary: str) -> list[Verdict]:
    speakers = {s.speaker for s in segs}
    units = build_units(segs, speakers)
    out = []
    for c in parse_summary(summary, speakers):
        if not c.person:
            out.append(Verdict(c, "NO_SPEAKER", note="no person named; not checked"))
            continue
        scored = []
        for u in units:
            if not c.toks:
                break
            cov = len(c.toks & u.toks) / len(c.toks)
            who = u.owner if c.kind == "commitment" else u.speaker
            if c.kind == "statement" and u.handoff:
                continue
            scored.append((cov, who, u))
        scored.sort(key=lambda x: (-x[0], x[2].handoff is False))
        if not scored or scored[0][0] < SUPPORT_MIN:
            best = scored[0] if scored else (0.0, None, None)
            out.append(Verdict(c, "UNSUPPORTED", coverage=round(best[0], 2), evidence=best[2],
                               note="nothing in the transcript backs this — possible hallucination"))
            continue
        top = [x for x in scored if x[0] >= max(SUPPORT_MIN, scored[0][0] - TIE)]
        mine = next((x for x in top if x[1] == c.person), None)
        if mine:
            out.append(Verdict(c, "SUPPORTED", c.person, mine[2], round(mine[0], 2)))
            continue
        cov, who, u = top[0]
        note = f"{c.person} isn't a speaker in this recording (name carried over from another meeting?)" \
            if c.person not in speakers else ""
        if c.kind == "commitment" and u.handoff:
            note = note or f"{u.speaker} asked, {who} accepted — the task is {who}'s"
        out.append(Verdict(c, "MISATTRIBUTED", who, u, round(cov, 2), note))
    return out


def repair(summary: str, verdicts: list[Verdict]) -> str:
    lines = summary.splitlines()
    for v in verdicts:
        ln = lines[v.claim.line_no]
        if v.label == "SUPPORTED":
            lines[v.claim.line_no] = f"{ln} [{mmss(v.evidence.start)}]"
        elif v.label == "MISATTRIBUTED":
            fixed = re.sub(rf"\b{re.escape(v.claim.person)}\b", v.correct, ln, count=1)
            if v.claim.kind == "commitment" and re.search(r"\basked \w+ to\b", ln):
                fixed = re.sub(rf"asked {re.escape(v.claim.person)} to", f"asked {v.correct} to", ln)
            lines[v.claim.line_no] = f"{fixed} [{mmss(v.evidence.start)}] (fixed: was {v.claim.person})"
        elif v.label == "UNSUPPORTED":
            lines[v.claim.line_no] = f"{ln} [not found in transcript — check]"
    return "\n".join(lines)
