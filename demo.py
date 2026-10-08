"""python demo.py  -> verdicts for every meeting, benchmark score, out/report.html"""
from __future__ import annotations

from html import escape
from pathlib import Path

from attribution_check.bench import run
from attribution_check.core import mmss, repair

HERE = Path(__file__).parent
COLOR = {"SUPPORTED": "ok", "MISATTRIBUTED": "bad", "UNSUPPORTED": "warn", "NO_SPEAKER": "mut"}

CSS = """
:root{--bg:#fbfaf8;--fg:#1c1b19;--mut:#6f6c66;--line:#e6e3dd;--card:#fff;--ok:#1d7a4f;--bad:#c2412d;--warn:#a56a12}
@media (prefers-color-scheme:dark){:root{--bg:#121211;--fg:#eceae4;--mut:#9a978f;--line:#2b2a27;--card:#1a1a18;--ok:#58c08d;--bad:#ef7a66;--warn:#e2ad55}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:32px 16px}h1{font-size:26px;margin:0}h2{font-size:18px;margin:0 0 10px}
.mut{color:var(--mut)}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0 28px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}.kpi b{display:block;font-size:28px}
.m{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:0 0 18px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:800px){.cols{grid-template-columns:1fr}}
.seg{font-size:14px;margin:0 0 6px}.seg b{display:inline-block;min-width:54px}.t{font:12px ui-monospace,monospace;color:var(--mut);margin-right:6px}
.v{border-left:3px solid var(--line);padding:6px 10px;margin:0 0 8px;font-size:14px}
.v.ok{border-color:var(--ok)}.v.bad{border-color:var(--bad)}.v.warn{border-color:var(--warn)}
.lab{font:600 11px ui-monospace,monospace;letter-spacing:.03em}.ok .lab{color:var(--ok)}.bad .lab{color:var(--bad)}.warn .lab{color:var(--warn)}
pre{white-space:pre-wrap;font:13px/1.5 ui-monospace,monospace;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;margin:10px 0 0}
"""


def block(doc, segs, verdicts) -> str:
    tr = "".join(f"<div class=seg><span class=t>{mmss(s.start)}</span><b>{escape(s.speaker)}</b> {escape(s.text)}</div>" for s in segs)
    vs = ""
    for v in verdicts:
        extra = ""
        if v.label == "MISATTRIBUTED":
            extra = f" → <b>{escape(v.correct)}</b> at {mmss(v.evidence.start)}"
        elif v.label == "SUPPORTED":
            extra = f" · {mmss(v.evidence.start)}"
        note = f"<div class=mut>{escape(v.note)}</div>" if v.note else ""
        vs += (f"<div class='v {COLOR[v.label]}'><span class=lab>{v.label}</span>{extra}<div>{escape(v.claim.text[2:])}</div>{note}</div>")
    return (f"<div class=m><h2>{escape(doc['title'])}</h2><div class=cols><div><div class=mut>Transcript (speaker tags correct)</div>{tr}</div>"
            f"<div><div class=mut>Summary, checked line by line</div>{vs}<div class=mut>Repaired summary</div>"
            f"<pre>{escape(repair(doc['summary'], verdicts))}</pre></div></div></div>")


def main() -> None:
    sc, results = run(HERE / "data" / "meetings")
    st, stress = run(HERE / "data" / "stress")

    for doc, segs, verdicts in results + stress:
        print(f"\n== {doc['title']}")
        for v in verdicts:
            tag = {"SUPPORTED": "  ok ", "MISATTRIBUTED": " FIX ", "UNSUPPORTED": " ??? "}.get(v.label, "  -  ")
            fix = f" -> {v.correct} @ {mmss(v.evidence.start)}" if v.label == "MISATTRIBUTED" else ""
            print(f" [{tag}] {v.claim.text[2:72]}{fix}")
    print(f"\nBenchmark (6 meetings, {sc.lines} summary lines, {sc.planted} planted errors): "
          f"caught {sc.caught}/{sc.planted}, false alarms {sc.false_alarms}")
    print(f"Paraphrase stress test: caught {st.caught}/{st.planted} with the right label; misses:")
    for m in st.misses:
        print("  ", m)

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    html = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Summary Attribution Check</title><style>{CSS}</style></head><body><main>
<h1>Summary attribution check</h1><div class=mut>Synthetic meetings · unofficial prototype by Kushagra Pratap Singh</div>
<div class=kpis><div class=kpi><span class=mut>Summary lines checked</span><b>{sc.lines}</b></div>
<div class=kpi><span class=mut>Planted errors caught</span><b>{sc.caught}/{sc.planted}</b></div>
<div class=kpi><span class=mut>False alarms</span><b>{sc.false_alarms}</b></div>
<div class=kpi><span class=mut>Paraphrase stress test</span><b>{st.caught}/{st.planted}</b></div></div>
{''.join(block(*r) for r in results + stress)}</main></body></html>"""
    (out / "report.html").write_text(html, encoding="utf-8")
    print(f"\nreport: {out / 'report.html'}")


if __name__ == "__main__":
    main()
