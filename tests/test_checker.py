from pathlib import Path

import pytest

from attribution_check.bench import load, run
from attribution_check.cited import validate_cited
from attribution_check.core import Segment, check, repair, tokens

DATA = Path(__file__).resolve().parents[1] / "data"


def segs(*rows):
    return [Segment(i, sp, t, x) for i, (sp, t, x) in enumerate(rows)]


def test_benchmark_catches_all_planted_errors_without_false_alarms():
    sc, _ = run(DATA / "meetings")
    assert sc.planted == 18
    assert sc.caught == 18, sc.misses
    assert sc.false_alarms == 0, sc.misses


def test_paraphrase_miss_still_goes_to_review():
    # Known limit of word matching: a paraphrase is labeled UNSUPPORTED, not MISATTRIBUTED —
    # it's still flagged, never silently passed.
    _, results = run(DATA / "stress")
    labels = [v.label for v in results[0][2]]
    assert "SUPPORTED" not in labels


def test_handoff_owner_is_the_person_who_accepted():
    s = segs(("Priya", 0, "Dev, can you send Tom the SOC 2 report?"), ("Dev", 5, "Sure, I'll do it today."))
    v = check(s, "- Priya: send Tom the SOC 2 report.")[0]
    assert (v.label, v.correct) == ("MISATTRIBUTED", "Dev")
    assert check(s, "- Dev: send Tom the SOC 2 report.")[0].label == "SUPPORTED"


def test_declined_request_is_not_a_handoff():
    s = segs(("Priya", 0, "Dev, can you send the SOC 2 report?"), ("Dev", 5, "I can't this week, I'm out."))
    assert check(s, "- Dev: send the SOC 2 report.")[0].label != "SUPPORTED"


def test_statement_vs_commitment():
    s = segs(("Anna", 0, "I'll write the discussion questions."), ("Mark", 9, "I found chapter four hard to read."))
    assert check(s, "- Mark said chapter four was hard to read.")[0].label == "SUPPORTED"
    v = check(s, "- Mark: write the discussion questions.")[0]
    assert (v.label, v.correct) == ("MISATTRIBUTED", "Anna")


def test_name_from_another_recording_is_flagged():
    doc, s = load(DATA / "meetings" / "05-interview.json")
    v = check(s, doc["summary"])[0]
    assert v.label == "MISATTRIBUTED" and v.correct == "Chris" and "isn't a speaker" in v.note


def test_unsupported_claim():
    s = segs(("Omar", 0, "The queue backed up, latency hit forty seconds."))
    assert check(s, "- Omar: migrate the queue to Kafka.")[0].label == "UNSUPPORTED"


def test_lines_without_a_person_are_skipped():
    s = segs(("Omar", 0, "The queue backed up."))
    assert check(s, "- The team discussed the queue.")[0].label == "NO_SPEAKER"


def test_repair_fixes_name_and_adds_timestamp():
    s = segs(("Anna", 134, "I'll write the discussion questions for chapter four."))
    summary = "## Action items\n- Mark: write the discussion questions for chapter four."
    fixed = repair(summary, check(s, summary))
    assert "- Anna: write the discussion questions" in fixed and "[02:14]" in fixed and "was Mark" in fixed


def test_tokens_handle_contractions_and_stems():
    assert tokens("I'll be sending the invites") == tokens("send invite")


@pytest.mark.parametrize("summary,problem", [
    ("## Action items\n- Priya: send the SOC 2 report. [S0]", "names Priya but cited line is Dev"),
    ("## Action items\n- Dev: send the SOC 2 report.", "no citation"),
    ("## Action items\n- Dev: send the SOC 2 report. [S9]", "doesn't exist"),
])
def test_cited_summary_validator(summary, problem):
    s = segs(("Priya", 0, "Dev, can you send the SOC 2 report?"), ("Dev", 5, "Sure."))
    probs = validate_cited(s, summary)
    assert probs and problem in probs[0]["problem"]


def test_cited_summary_validator_passes_correct_citation():
    s = segs(("Priya", 0, "Dev, can you send the SOC 2 report?"), ("Dev", 5, "Sure."))
    assert validate_cited(s, "## Action items\n- Dev: send the SOC 2 report. [S0]") == []
