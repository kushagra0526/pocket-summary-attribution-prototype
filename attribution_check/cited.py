"""Fix it at the source: ask the summarizer to cite transcript lines, then check the citations.

Each bullet must end with [S<n>] tags. The validator checks that the person named in the bullet
actually said (or, for tasks, accepted) the cited line. An unchecked citation is no better than
no citation.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from .core import Segment, build_units, mmss, parse_summary

PROMPT = """You are summarizing a recorded conversation. Each transcript line has an id like [S3] and a speaker.

Write:
## Summary
- 3-6 bullets of the form "<Speaker> said/explained ...". End each with the ids it came from, e.g. [S3].
## Action items
- "<Owner>: <task>" [S<n>]. The owner is whoever agreed to do it, NOT whoever asked for it.

Only use speaker names that appear in the transcript. Never merge two people.

Transcript:
{lines}"""


def transcript_lines(segs: list[Segment]) -> str:
    return "\n".join(f"[S{s.idx}] {mmss(s.start)} {s.speaker}: {s.text}" for s in segs)


def validate_cited(segs: list[Segment], summary: str) -> list[dict]:
    speakers = {s.speaker for s in segs}
    by_id = {s.idx: s for s in segs}
    owner = {s.idx: s.speaker for s in segs}
    for u in build_units(segs, speakers):
        if u.handoff:
            owner[u.seg_ids[0]] = u.owner
    problems = []
    for c in parse_summary(summary, speakers):
        ids = [int(x) for x in re.findall(r"\[S(\d+)\]", c.text)]
        if not c.person:
            continue
        if not ids:
            problems.append({"line": c.text, "problem": "no citation"})
            continue
        if any(i not in by_id for i in ids):
            problems.append({"line": c.text, "problem": "cites a line that doesn't exist"})
            continue
        who = {owner[i] if c.kind == "commitment" else by_id[i].speaker for i in ids}
        if c.person not in who:
            problems.append({"line": c.text, "problem": f"names {c.person} but cited line is {', '.join(sorted(who))}"})
    return problems


def llm_summary(segs: list[Segment]) -> str:  # pragma: no cover - needs a key
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("set GROQ_API_KEY to generate a cited summary")
    body = {"model": os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"), "temperature": 0,
            "messages": [{"role": "user", "content": PROMPT.format(lines=transcript_lines(segs))}]}
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", json.dumps(body).encode(),
                                 {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]
