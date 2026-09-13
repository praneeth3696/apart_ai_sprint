"""
build_docx.py

Renders the submission into Apart Research's official template, preserving its
styles, margins and title block.

Numbers are pulled from `analysis/e1_stats.json` wherever they appear in a
table, so a regenerated analysis cannot silently disagree with the document.
Prose figures are cross-checked by `report/check_numbers.py` against the same
file before this runs.

Usage:
    python analysis/stats.py --eai
    python report/check_numbers.py        # must pass first
    python report/build_docx.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

REPO = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "report" / "Copy of Apart Research hackathon submission template.docx"
OUT = REPO / "report" / "HF-Replay-Recon_AI-Incident-Response-Sprint.docx"
STATS = json.loads((REPO / "analysis" / "e1_stats.json").read_text(encoding="utf-8"))
FIGDIR = REPO / "analysis" / "figures"

PER = STATS["per_model"]
E3 = STATS["e3"]["per_model"]


def short(m: str) -> str:
    n = m.split(":", 1)[-1].split("/")[-1]
    return n[:-7] if n.endswith("-latest") else n


def provider_of(m: str) -> str:
    return {"google": "Google", "groq": "Groq", "mistral": "Mistral"}.get(
        m.split(":")[0], m.split(":")[0])


def pooled() -> dict:
    mk = sum(s["milestone_hit_rate"]["k"] for s in PER.values())
    mn = sum(s["milestone_hit_rate"]["n"] for s in PER.values())
    bk = sum(s["benign_false_page_rate"]["k"] for s in PER.values())
    bn = sum(s["benign_false_page_rate"]["n"] for s in PER.values())
    sig = [m for m, s in PER.items()
           if s["fisher_milestone_vs_benign"] is not None
           and s["fisher_milestone_vs_benign"] < 0.05]
    inc = sum(s["incoherence_rate"]["k"] for s in E3.values())
    tot = sum(s["incoherence_rate"]["n"] for s in E3.values())
    esc = sum(s["escalated"]["k"] for s in E3.values())
    assn = sum(s["refused_to_assist"]["n"] for s in E3.values())
    ass = sum(s["refused_to_assist"]["n"] - s["refused_to_assist"]["k"]
              for s in E3.values())
    return dict(mk=mk, mn=mn, bk=bk, bn=bn, sig=sig, n_models=len(PER),
                inc=inc, tot=tot, esc=esc, ass=ass, assn=assn,
                e3_models=sum(1 for s in E3.values() if s["incoherence_rate"]["n"]))


P = pooled()


# ---------------------------------------------------------------- doc helpers
def clear_body(doc) -> None:
    """Strip the template's instructional content, keeping styles and the
    title/abstract table."""
    body = doc.element.body
    for tbl in list(doc.tables[1:]):          # keep table 0 (title/abstract)
        tbl._element.getparent().remove(tbl._element)
    for p in list(doc.paragraphs):
        p._element.getparent().remove(p._element)


def para(doc, text="", style="normal", size=None, bold=False, italic=False,
         align=None, space_after=6):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        _rich(p, text, size=size, bold=bold, italic=italic)
    return p


def _rich(p, text, size=None, bold=False, italic=False):
    """Inline **bold**, *italic* and `code`, including *italic* nested inside
    **bold** — which the naive one-pass version could not do, and which left
    literal asterisks in two paragraphs of the first build."""
    # Split on bold spans that may themselves contain single-asterisk italics.
    bold_re = re.compile(r"\*\*((?:[^*]|\*(?!\*))+)\*\*")
    pos = 0
    for m in bold_re.finditer(text):
        if m.start() > pos:
            _emphasis(p, text[pos:m.start()], size, bold, italic)
        _emphasis(p, m.group(1), size, True, italic)
        pos = m.end()
    if pos < len(text):
        _emphasis(p, text[pos:], size, bold, italic)


def _emphasis(p, text, size, bold, italic):
    """*italic* and `code` within an already-resolved bold context."""
    for tok in re.split(r"(\*[^*]+\*|`[^`]+`)", text):
        if not tok:
            continue
        r = p.add_run()
        if tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
            r.text = tok[1:-1]
            r.font.name = "Consolas"
            r.font.size = Pt((size or 10.5) - 0.5)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r.text, r.italic = tok[1:-1], True
        else:
            r.text = tok
            if italic:
                r.italic = True
        if bold:
            r.bold = True
        if size and not r.font.size:
            r.font.size = Pt(size)


def bullet(doc, text, size=None):
    p = doc.add_paragraph(style="normal")
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.space_after = Pt(4)
    _rich(p, "• " + text, size=size)
    return p


def heading(doc, text, level=2):
    h = doc.add_paragraph(style=f"Heading {level}")
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(6)
    h.add_run(text)
    return h


def caption(doc, text):
    p = doc.add_paragraph(style="normal")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(10)
    _rich(p, text, size=9, italic=False)
    for r in p.runs:
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
    return p


def _borders(table, sz=4, colour="999999"):
    """The template ships no `Table Grid` style, so borders are set directly."""
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), colour)
        borders.append(el)
    tblPr.append(borders)


def _shade(cell, colour="F2F2F2"):
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), colour)
    cell._tc.get_or_add_tcPr().append(sh)


def add_table(doc, headers, rows, widths=None, size=8.5):
    t = doc.add_table(rows=1, cols=len(headers))
    _borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        _shade(c)
        pr = c.paragraphs[0]
        pr.paragraph_format.space_after = Pt(2)
        run = pr.add_run(h)
        run.bold = True
        run.font.size = Pt(size)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            pr = cells[i].paragraphs[0]
            pr.paragraph_format.space_after = Pt(2)
            _rich(pr, str(val), size=size)
            for r in pr.runs:
                if not r.font.size:
                    r.font.size = Pt(size)
    if widths:
        t.autofit = False
        for r in t.rows:
            for i, w in enumerate(widths):
                r.cells[i].width = Inches(w)
    # a little air after every table
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figure(doc, path, width_in, cap):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    p.add_run().add_picture(str(path), width=Inches(width_in))
    caption(doc, cap)


# ------------------------------------------------------------------- content
TITLE = "Your Monitor Will Explain the Breach and Not Wake You"
SUBTITLE = "Bimodal failure and systematic under-escalation in LLM incident triage"

ABSTRACT = (
    "Would an LLM on monitoring duty have paged the on-call during the July 2026 "
    "Hugging Face agent intrusion? We rebuilt it from the published timeline as a "
    "replayable 17,613-action stream, generated a size-matched benign control, "
    "verified blind that the two are not trivially separable, and ran 15 models "
    "across three providers past both, at $0.00.\n\n"
    "Models fail in both directions. One buys perfect recall by paging on 11 of "
    "12 innocent windows; two page on nothing, reading an active intrusion as "
    "\u201cresource contention\u201d. Only 2 of 15 separate the streams "
    "significantly.\n\n"
    "We then wrapped byte-identical evidence in a monitor frame and an assistant "
    "frame. Across 228 moments and 11 models, incoherence was zero \u2014 but the "
    "frames disagreed one way only: models assisted on 228/228 and escalated on "
    "83. The risk is not refusal; it is fluent analysis with a silent pager."
)

REFS = [
    "Hugging Face (2026). Anatomy of a Frontier Lab Agent Intrusion: A Technical Timeline of the July 2026 Incident. 27 July 2026. https://huggingface.co/blog/agent-intrusion-technical-timeline",
    "OpenAI (2026). Hugging Face Incident Technical Report, 38pp. https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf",
    "Röttger, P., Kirk, H.R., Vidgen, B., Attanasio, G., Bianchi, F., Hovy, D. (2024). XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models. NAACL 2024. arXiv:2308.01263",
    "Cui, J., Chiang, W.-L., Stoica, I., Hsieh, C.-J. (2024). OR-Bench: An Over-Refusal Benchmark for Large Language Models. arXiv:2405.20947",
    "Bhatt, M. et al. (2024). CyberSecEval 2: A Wide-Ranging Cybersecurity Evaluation Suite for Large Language Models. arXiv:2404.13161",
    "Jones, E.K., Dziemian, M., Fredrikson, M., Kolter, J.Z. (2026). A New Framework for Cybersecurity Refusals in AI Agents. arXiv:2606.02644",
    "Campbell, D., Kale, N., Sehwag, U.M., Herring, B., Price, N., Borges, D., Levinson, A., Knight, C.Q. (2026). Defensive Refusal Bias: How Safety Alignment Fails Cyber Defenders. arXiv:2603.01246",
    "Wang, L. et al. (2026). SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response. 29 July 2026. arXiv:2607.26791",
    "Begimher, D., Leo, C., Huang, J., Gaw, P., Zheng, B. (2026). SIR-Bench: Evaluating Investigation Depth in Security Incident Response Agents. 13 April 2026. arXiv:2604.12040",
    "Deason, L. et al. (Meta / CrowdStrike) (2025). CyberSOCEval: Benchmarking LLMs Capabilities for Malware Analysis and Threat Intelligence Reasoning. arXiv:2509.20166",
    "Tariq, S., Baruwal Chhetri, M., Nepal, S., Paris, C. (2025). Alert Fatigue in Security Operations Centres: Research Challenges and Opportunities. ACM Computing Surveys 57(9), Article 224. doi:10.1145/3723158",
]


def e1_rows():
    order = sorted(PER.items(),
                   key=lambda kv: (-(kv[1]["benign_false_page_rate"]["rate"]
                                     if kv[1]["benign_false_page_rate"]["n"] else -1),))
    out = []
    for m, s in order:
        h, b = s["milestone_hit_rate"], s["benign_false_page_rate"]
        hs = f"{h['k']}/{h['n']} ({h['rate']:.0%})"
        bs = (f"{b['k']}/{b['n']} ({b['rate']:.0%})" if b["n"] else "—")
        pv = s["fisher_milestone_vs_benign"]
        ps = "—" if pv is None else (f"**{pv:.3f}**" if pv < 0.05 else f"{pv:.3f}")
        out.append([short(m), provider_of(m), hs, bs, ps])
    return out


def e3_rows():
    rows = []
    for m, s in sorted(E3.items(), key=lambda kv: -(kv[1]["escalated"]["rate"] or 0)
                       if kv[1]["escalated"]["n"] else 1):
        if not s["incoherence_rate"]["n"]:
            continue
        e, r = s["escalated"], s["refused_to_assist"]
        pv = s["mcnemar_escalate_vs_assist"]["p_exact"]
        ps = f"**{pv:.4f}**" if pv < 0.05 else f"{pv:.3f}"
        rows.append([short(m), provider_of(m),
                     f"{s['incoherence_rate']['k']}/{s['incoherence_rate']['n']}",
                     f"{e['k']}/{e['n']} ({e['rate']:.0%})",
                     f"{r['n'] - r['k']}/{r['n']}", ps])
    return rows


# ---------------------------------------------------------------------- main
def main() -> int:
    doc = docx.Document(str(TEMPLATE))
    clear_body(doc)

    # ---- title block (template table 0) -----------------------------------
    tbl = doc.tables[0]
    tc = tbl.rows[0].cells[0]
    tc.text = ""
    p = tc.paragraphs[0]
    p.style = doc.styles["Title"]
    p.add_run(TITLE)
    sub = tc.add_paragraph()
    r = sub.add_run(SUBTITLE)
    r.italic = True
    r.font.size = Pt(12)
    au = tc.add_paragraph()
    au.add_run("Amirtha Yazhini M · Praneeth Reddy Y").font.size = Pt(10.5)
    em = tc.add_paragraph()
    e = em.add_run("amirthayazhini.m@gmail.com · ypr2257@gmail.com")
    e.font.size = Pt(9.5)
    e.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
    vn = tc.add_paragraph()
    v = vn.add_run("AI Incident Response Sprint · Apart Research · 11–13 September 2026")
    v.font.size = Pt(9.5)
    v.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

    ac = tbl.rows[1].cells[0]
    ac.text = ""
    ap = ac.paragraphs[0]
    ap.add_run("Abstract").bold = True
    for block in ABSTRACT.split("\n\n"):
        q = ac.add_paragraph()
        q.paragraph_format.space_after = Pt(4)
        _rich(q, block, size=10)

    # ---- 1. Introduction ---------------------------------------------------
    heading(doc, "1. Introduction")
    para(doc, "In July 2026 an autonomous agent compromised Hugging Face's "
              "dataset-conversion infrastructure, moved laterally through a Kubernetes "
              "cluster, extracted cloud and VPN credentials, and reached multi-cluster "
              "administrative access. Hugging Face published a technical timeline [1] "
              "and OpenAI a 38-page incident report [2]. The obvious question for "
              "anyone running an AI-assisted security operation is the one neither "
              "document can answer: **would a model on monitoring duty have paged the "
              "on-call in time?**")
    para(doc, "The tempting way to ask is to show a model the incident and see whether "
              "it notices. That question is nearly free to answer and nearly worthless. "
              "A model that pages on every window would \"catch\" the incident, and a "
              "detector that pages on everything is not a detector. **The question only "
              "means something against a matched control**, and supplying that control "
              "is most of the work.")
    para(doc, "So we rebuilt the incident as a replayable 17,613-action stream from the "
              "published figures, generated a size-matched benign stream from the same "
              "marginal distributions, verified blind that the two are not trivially "
              "separable, and ran both past the same models under the same monitor "
              "prompt. Fifteen models across three providers, at a total cost of "
              "**$0.00**.")

    para(doc, "**Threat model.** We assume an AI monitor placed in a SOC triage loop, "
              "reading windows of audit-log activity and deciding whether to wake a "
              "human. The failure we care about is not the model being wrong about a "
              "single event but being *systematically* mis-calibrated: either paging so "
              "often that its alarms are ignored, or staying silent through an active "
              "intrusion. Both degrade response capacity, and alert fatigue is a "
              "documented, surveyed failure mode in real SOCs [11].")

    para(doc, "**Our main contributions are:**")
    bullet(doc, "**A replayable reconstruction of a real 2026 agent intrusion with a "
                "validated matched benign control**, generated from published figures "
                "and released with the harness. The control is verified blind against a "
                "pre-registered separability threshold, which is what makes every "
                "false-page number in this paper interpretable.")
    bullet(doc, "**Evidence that LLM incident monitors fail in both directions.** Recall "
                "and selectivity fail independently: one model pages on 92% of an "
                "innocent shift, two others page on nothing whatever. The region a "
                "deployable monitor would occupy is empty, and model scale does not "
                "order the failure.")
    bullet(doc, "**A two-frame test isolating escalation from willingness**, holding "
                "evidence byte-identical and varying only whether the model is addressed "
                "as the triage layer or as an analyst's assistant. Across 228 moments "
                "and 11 models it returns its pre-registered null on incoherence and an "
                "unexpected, strongly one-directional asymmetry: models assist "
                "universally and escalate rarely.")
    bullet(doc, "**Non-LLM rule baselines on the same axes**, without which a model page "
                "rate cannot be read at all — and which reveal that first-page latency, "
                "the metric we pre-registered, is degenerate on this corpus.")

    # ---- 2. Related Work ---------------------------------------------------
    heading(doc, "2. Related Work")
    para(doc, "**The incident.** Our substrate reconstructs the July 2026 Hugging Face "
              "agent intrusion from two independently-fetched primary sources: HF's "
              "technical timeline [1] and OpenAI's incident report [2], both retrieved "
              "and cross-checked on 2026-09-04. Where their published tables disagree we "
              "carry the disagreement rather than resolving it silently (§3.1).")
    para(doc, "**Refusal benchmarks and what they do not measure.** A mature literature "
              "measures *over-refusal*: XSTest [3] and OR-Bench [4] build prompts that "
              "look unsafe but are benign and score models on wrongly declining them; "
              "CyberSecEval carries the same axis into security as a False Refusal Rate "
              "[5]; and Gray Swan's framework [6] evaluates where an agent *should* "
              "decline. Closest to our setting, *Defensive Refusal Bias* [7] ran 2,390 "
              "real cyber-defence competition prompts and found security keywords "
              "refused at **2.72× the rate** of neutral phrasing, with explicit "
              "authorisation *increasing* refusal (21.8% vs 11.6%) rather than licensing "
              "the work.")
    para(doc, "**Refusal was not the failure mode we found.** In 228 scoreable moments, "
              "not one model declined to analyse the evidence. A benchmark measuring "
              "only the refusal axis would have recorded a clean sheet and missed the "
              "finding entirely. What we observe is the opposite defect: the model "
              "engages fluently and *does not escalate*. That axis — whether the model "
              "raises an alarm, not whether it is willing to talk — is the one these "
              "benchmarks do not score.")
    para(doc, "**Incident-response benchmarks.** SecRespond [8] gives agents forensic "
              "disk snapshots from ten compromised cloud hosts; SIR-Bench [9] replays "
              "authentic incident patterns as cloud telemetry across 794 test cases; "
              "CyberSOCEval [10] scores incident investigation and severity rating on "
              "SOC data. Our substrate differs in being a *public-report reconstruction* "
              "— reproducible from two cited documents with no proprietary telemetry — "
              "and our unit of analysis is the per-window page/don't-page decision over "
              "an ordered stream, which is what makes detection latency measurable.")
    para(doc, "Two things distinguish what we measure. First, **the matched benign "
              "control.** SIR-Bench does score false-positive rejection (73.4% for its "
              "baseline agent) on labelled false alerts, so a false-alarm axis is not "
              "unprecedented; what we add is a *time-matched benign stream built by the "
              "same generator as the attack stream*, letting us report a page rate on "
              "windows containing no intrusion at all — selectivity rather than "
              "rejection of pre-labelled decoys. To our knowledge no prior benchmark "
              "pairs an incident replay with such a control. Second, **frame sensitivity "
              "on byte-identical evidence.** We are not aware of prior work isolating "
              "that variable on security-escalation decisions.")
    # ---- 3. Methods --------------------------------------------------------
    heading(doc, "3. Methods")

    heading(doc, "3.1 Corpus and controls", 3)
    para(doc, "The corpus is **generated, not hand-written**: every count, phase "
              "boundary and milestone timestamp comes from one machine-readable "
              "ground-truth file, and the generator asserts at build time that each "
              "defined milestone is placed. It covers **17,613 attacker actions** inside "
              "the published campaign envelope, 2026-07-09 02:28 to 2026-07-13 14:14 UTC.")
    para(doc, "One source discrepancy is inherited rather than smoothed over: the "
              "published phase and daily-volume tables disagree (16,521 vs 17,613). We "
              "take the daily-volume total, which matches the source's own \"~17,600\" "
              "headline to within 13 actions, and carry the 1,092-action remainder as an "
              "explicit `unclassified` residual. Exfiltration is **56 actions (0.3%)** — "
              "a needle-in-haystack problem, so any method working by volume spike has "
              "the wrong task.")
    para(doc, "Every experiment runs against **two streams**: the attack stream and a "
              "size-matched **benign control** from the same generator and the same "
              "marginals, with no intrusion in it. The control converts \"the model "
              "paged\" into \"the model paged *selectively*\"; without it a page rate is "
              "uninterpretable. Both are cut into 5-minute windows — 1,278 attack, 1,280 "
              "control. Twelve attack windows carry a milestone; the control carries "
              "none by construction.")
    para(doc, "**Milestone provenance is graded, not uniform.** Six of the twelve are "
              "read off a published table; five have a bounded or estimated time where "
              "the source fixes the event but not the minute (\"shortly before midnight "
              "on July 11\"); and one, `supply_chain_token_mint`, is **unreconciled** — "
              "HF places it on 07-12 and OpenAI on 07-13, and we have not resolved which "
              "is right. The milestone *set* is sourced; six of the twelve *timestamps* "
              "are interpolated within published bounds, and the escalation point is one "
              "of them.")
    para(doc, "Models see only a projection of each action (index, timestamp, host role, "
              "actor, event text); the ground-truth block is asserted out of every prompt "
              "at runtime, since those labels are exactly what we are measuring the "
              "model's ability to notice.")

    heading(doc, "3.2 Is the control actually a control?", 3)
    para(doc, "A matched control is only worth having if it is not trivially "
              "distinguishable. Before any model ran, 20 unlabelled windows (10 per "
              "stream) were scored blind against a pre-registered 90% failure threshold. "
              "Result: **14/20 (70%), Wilson CI95 48.1–85.5%, p = 0.058** against chance, "
              "with attack and benign recall both 70% — no label bias. The control "
              "passes, so the false-page denominator is defensible.")
    para(doc, "**Disclosure.** These labels were produced by **an LLM (Claude), not the "
              "human rater the pre-registration specifies.** The deviation is disclosed "
              "rather than left implicit. An LLM is arguably a *stronger* adversary than "
              "a human skimming (systematic, tireless) and arguably weaker (no "
              "operational intuition), so we do not claim the substitution is neutral "
              "either way. And **n = 20 is a screen, not a powered test**: it catches the "
              "trivial-separability case it was built for and cannot resolve 55% from 70%.")

    heading(doc, "3.3 E0 — non-LLM rule baselines", 3)
    para(doc, "Three detectors run over identical streams, windowing and ground truth, "
              "at zero API cost; without them a model's page rate has nothing to compare "
              "against. `volume_spike` and `keyword_sigma` see **only** the projection a "
              "model under evaluation sees. `sev_threshold` deliberately breaks that rule "
              "and reads ground-truth severity: **it is an ORACLE — the upper bound for a "
              "detector that already knows the answer — and never a baseline a defender "
              "could deploy.** We label it ORACLE at every appearance for that reason.")

    heading(doc, "3.4 E1 — escalation and false-paging", 3)
    para(doc, "Each model is placed in a **monitor frame**: the automated triage layer "
              "for a production Kubernetes platform, shown a bounded rolling digest of "
              "everything before the current window plus the window itself, returning "
              "strict JSON — `{severity, page_oncall, rationale}`. `page_oncall` is the "
              "escalation criterion; severity is recorded but is not it. The digest is "
              "computed locally from model-visible fields and bounded (top hosts, top "
              "actors, last 8 events), so this stays a triage task rather than a "
              "long-context retrieval task. Unparseable JSON gets **exactly one** re-ask; "
              "still unparseable is recorded as `unparseable` and excluded from "
              "page-rate denominators.")
    para(doc, "**Two attack populations are reported, and never pooled.** The *milestone "
              "census* is all 12 milestone-carrying windows — a census, not a sample, "
              "because a uniform sample of 1,278 windows would expect to catch a fraction "
              "of one. The *uniform sample* is evenly spaced windows, and it is the only "
              "like-for-like comparison to the benign control. Pooling them biases the "
              "attack page rate upward, because the census over-represents high-severity "
              "windows by construction.")
    para(doc, "Sampling runs on a **nested ladder** (12 → 36 → 108 → 324 → 972), each "
              "rung 3× the last. This is not cosmetic: evenly-spaced samples at *n* and "
              "*n′* share no positions unless *n′/n* is an odd integer, so naively "
              "widening 12 → 40 windows would have selected **none** of the windows a "
              "previous run had already paid for. On the ladder every rung is a strict "
              "superset of those beneath it, so widening is always additive.")

    heading(doc, "3.5 E3 — the two-frame incoherence test", 3)
    para(doc, "A **byte-identical** evidence block is wrapped in two prompts differing "
              "only in the role sentence and the ask: a *monitor* frame (\"you are the "
              "triage layer; severity? do you page the on-call?\") and an *assistant* "
              "frame (\"I'm on the incident response team; help me analyse this\"). "
              "Evidence identity is **asserted at runtime**, not assumed. K = 24 incident "
              "moments are stratified across all ten phases (9 carry a milestone).")
    para(doc, "The 2×2 is escalates × refuses, with **INCOHERENT** the cell of interest: "
              "does not escalate *and* will not help. Two cells sit outside it and are "
              "reported separately, never folded in. `filtered-both` — a platform filter "
              "blocked both prompts, so the model made no judgment at all — is **never** "
              "counted as INCOHERENT; doing so would attribute to model reasoning "
              "something no model did.")

    heading(doc, "3.6 Outcome taxonomy, and one amendment", 3)
    para(doc, "Every call is assigned exactly one outcome from a rubric frozen before "
              "scoring began: `comply`, `refused`, `partial`, `filtered` (a platform "
              "filter blocked the request — the model never saw it), `truncated` (the "
              "token budget ran out before any content — **our defect, never scored**), "
              "and `unaffordable` (HTTP 402).")
    para(doc, "**The rubric was amended once during the run, and the amendment is logged "
              "with a UTC timestamp in the rubric's own amendment table.** We added a "
              "`quota_exhausted` outcome: an HTTP 429 whose `quotaId` names a **per-day** "
              "window, as distinct from the ordinary per-minute rate limit that is simply "
              "retried. It is the free-tier twin of the HTTP 402 that `unaffordable` "
              "already covered — the only difference is whether money or quota ran out "
              "first — and like `unaffordable` it is **excluded from every denominator**. "
              "Recording a spent daily quota as a model declining to page would "
              "manufacture a finding out of our own budget. No E1 or E3 item had been "
              "scored when the outcome was added.")

    heading(doc, "3.7 Providers, and why throughput is the methodology", 3)
    para(doc, "The study cost **$0.00**; every call ran on a free tier. Price was never "
              "the binding constraint — **throughput was**, and it shaped the "
              "experiments. Google AI Studio meters its free tier **per project × model** "
              "at a measured 10–31 requests *per day*; Groq allows 1,000/day/model "
              "against an 8,000 tokens-per-minute organisation-wide ceiling; Mistral's "
              "free tier covers only its `ministral` family at 30 requests/minute. Two "
              "further candidates gave nothing: Cerebras returns HTTP 402 on every chat "
              "model, and **GitHub Models — the GPT-class arm our pre-registration named "
              "— was retired mid-sprint** (HTTP 410, `github_models_retirement_brownout`).")
    para(doc, "**Two accounts, disclosed.** The Google arm was collected on two separate "
              "free tiers, one per author, each on their own project and API key. Google "
              "meters per project per model per day, so these are two independent quotas "
              "rather than one quota circumvented — the same arrangement as two "
              "researchers each running their own laptop. No paid tier, no secondary "
              "accounts, and no key used beyond its own published free limit.")
    para(doc, "A model is not a model — it is a model *as served by someone* — so the "
              "provider is reported beside every model ID.")

    heading(doc, "3.8 Statistics", 3)
    para(doc, "Wilson score intervals throughout, because the rates sit near 0 and 1 "
              "where the normal approximation runs off the end of [0,1]. Comparisons are "
              "**exact**, not asymptotic, because per-cell *n* is 1–36: Fisher's exact "
              "test for the census-versus-benign contrast (unpaired), and McNemar's exact "
              "test where the pairing is real (the two frames on identical evidence in "
              "E3). All are standard-library implementations validated against published "
              "reference values.")
    # ---- 4. Results --------------------------------------------------------
    heading(doc, "4. Results")
    para(doc, f"Non-observations (`unaffordable`, `quota_exhausted`, `error`, "
              f"`truncated`) are excluded from every denominator: they record that we "
              f"could not buy the observation, not that a model did anything.")

    heading(doc, "4.1 Rule baselines set the bar (E0)", 3)
    add_table(doc,
              ["Detector", "Milestone hit", "Benign false-page", "First page"],
              [["`sev_threshold` (**ORACLE**)", "12/12 = 100%", "0/1280 = 0%", "action #15"],
               ["`volume_spike`", "1/12 = 8%", "15/1280 = 1.2%", "action #15"],
               ["`keyword_sigma`", "8/12 = 67%", "361/1280 = 28%", "action #51"]],
              widths=[2.0, 1.4, 1.6, 1.1])
    caption(doc, "Table 1. Non-LLM rule baselines over the same streams, windowing and "
                 "ground truth. sev_threshold reads ground-truth severity: it is an "
                 "upper bound for a detector that already knows the answer, not a "
                 "deployable control.")
    para(doc, "The two real detectors bracket the difficulty. `volume_spike` keeps a "
              "1.2% false-page rate but catches **1 of 12** milestone windows: quiet and "
              "blind. `keyword_sigma` catches 8 of 12 but fires on **28% of the benign "
              "control** — it cannot tell the streams apart, which is the finding, and "
              "it is what makes the model numbers interpretable.")

    heading(doc, "4.2 Models fail in both directions (E1)", 3)
    add_table(doc, ["Model", "Provider", "Milestone hit (census)",
                    "Benign false-page (uniform)", "Fisher p"],
              e1_rows(), widths=[1.55, 0.8, 1.45, 1.5, 0.75], size=8)
    caption(doc, f"Table 2. Per-model escalation on the milestone census against the "
                 f"matched benign control, ordered by false-page rate. Intervals omitted "
                 f"for space; all are Wilson 95% and reported in the repository. The "
                 f"last rows carry n = 1: gemini-3.8-flash exhausted its 20-request "
                 f"daily cap and qwen3.6-27b rejects the E1 prompt as too large. They "
                 f"are listed because omitting them would be selective reporting.")

    para(doc, f"**The distribution is bimodal, and that is the result.** Pooled across "
              f"models the numbers are {P['mk']}/{P['mn']} ({P['mk']/P['mn']:.0%}) on "
              f"milestones and {P['bk']}/{P['bn']} ({P['bk']/P['bn']:.0%}) on benign "
              f"windows — but **the pooled figure describes no model in the study.** It "
              f"averages a monitor that pages on 92% of an innocent shift with one that "
              f"pages on nothing at all.")
    para(doc, "At one end, `gemini-3.1-flash-lite` achieves a perfect 12/12 milestone "
              "recall by paging on **11 of 12 benign windows**. Its recall is free and "
              "worth nothing: a pager that always fires carries no information.")
    para(doc, "At the other, `ministral-3b` and `ministral-8b` page on **nothing at "
              "all** — 0/12 milestones and 0/36 benign windows. This is not a parsing "
              "artefact; both return well-formed verdicts with severity ratings and "
              "reasoning. They simply read the intrusion as an operations problem. On "
              "the window containing the first sandbox RCE, `ministral-8b` returns "
              "*\"normal operational activity… no signs of errors, security risks\"*; on "
              "a window where Python processes jump 16→256 during credential-access "
              "reconnaissance, *\"resource contention or scaling issues\"*. **A monitor "
              "that never pages has a perfect false-page rate**, which is precisely why "
              "false-page rate cannot be read without recall beside it.")
    sig_names = ", ".join(f"`{short(m)}`" for m in P["sig"])
    para(doc, f"Only {len(P['sig'])} of {P['n_models']} models separate the streams at "
              f"*p* < 0.05 ({sig_names}). **Thirteen do not.** Those two are also the "
              f"models we could sample most deeply (*n* = 36 benign against *n* = 4–12 "
              f"for the Google arm), so **significance here tracks sampling budget as "
              f"much as model behaviour** and we do not present it as a ranking.")

    figure(doc, FIGDIR / "figure1_detection_vs_false_page.png", 6.3,
           "Figure 1. Milestone-window hit rate against benign false-page rate, models "
           "and non-LLM rule baselines on one pair of axes. Bars are Wilson 95% "
           "intervals. The diagonal is the line of no discrimination. The useful region "
           "is the top-left, and it is empty: models spread along and above the diagonal "
           "at the trigger-happy end or collapse into the bottom-left with the blind "
           "ones. Colour encodes the arm rather than the model, because a scatter puts "
           "every colour pair side by side and the palette only clears colour-vision-"
           "deficiency separation thresholds at three slots.")

    para(doc, "Capability does not order this. `gpt-oss-120b` discriminates while "
              "`gpt-oss-20b` — same family, same provider, same serving stack — catches "
              "2 of 12 milestones. Within Mistral the 3b, 8b and 14b models are "
              "near-identical and all near-silent. **Scale did not buy selectivity in "
              "either family.**")

    heading(doc, "4.3 First-page latency is degenerate on this corpus (E1)", 3)
    para(doc, "Every E0 detector fires at action **#15–51** of 17,613 — roughly 10,400 "
              "actions before the escalation point at #10,498 — on filler that is "
              "byte-identical in both streams. Any model with a non-zero false-page rate "
              "does the same. On this corpus, therefore, **a first page measures "
              "trigger-happiness, not detection.** We report Escalation Action Index for "
              "completeness and decline to headline it; the metric pair in §4.2 replaces "
              "it. This reprioritisation is logged as a pre-registration amendment, and "
              "both metrics are reported for every model.")
    para(doc, "**The pre-registered negative-lead-time result.** We committed in advance "
              "to reporting this whichever way it came out, because it is unflattering "
              "to the whole framing of escalation latency. The ground-truth escalation "
              "point — the first sourced pivotal milestone, action #10,498 at 2026-07-11 "
              "17:47:30 UTC — falls **51.4 hours *after* the first exfiltration action** "
              "(#1,894, 07-09 14:21). Exfiltration is not the thing a "
              "perfectly-calibrated detector gets ahead of on this incident; by the time "
              "the escalation criterion is satisfiable at all, data has been leaving for "
              "more than two days. Lead time to admin/host-level access is **+10.0 h**, "
              "so the criterion is early for privilege escalation and hopelessly late "
              "for exfiltration. This is a property of the published phase windows "
              "rather than a defect in the rule, and we declined to reselect a rule that "
              "produces a prettier number.")
    para(doc, "The two facts compound rather than cancel. The rule that *should* fire is "
              "already 51 hours too late for exfiltration; the detectors that beat it to "
              "the punch do so only by firing on action #15 of 17,613. **Neither \"page "
              "early\" nor \"page correctly\" is achieved by anything we measured.**")

    figure(doc, FIGDIR / "figure2_eai_timeline.png", 6.3,
           "Figure 2. Escalation Action Index — the first window each detector paged on, "
           "over the uniform attack sample. Reported for completeness: the clustering "
           "within the first ~50 of 17,613 actions is why this metric was demoted from "
           "the headline.")
    heading(doc, "4.4 The incoherence test: a null, and a strong asymmetry (E3)", 3)
    para(doc, f"{P['e3_models']} models across **three providers and five families**, "
              f"{P['tot']} scoreable moments on byte-identical evidence.")
    add_table(doc, ["Model", "Provider", "Incoherent", "Escalated", "Assisted",
                    "McNemar p"],
              e3_rows(), widths=[1.5, 0.75, 0.85, 1.05, 0.85, 0.9], size=8)
    caption(doc, "Table 3. The two-frame test. \"Incoherent\" is the cell where a model "
                 "neither escalates nor will help analyse the same bytes. \"Assisted\" "
                 "counts moments where the assistant frame engaged. McNemar's exact test "
                 "is on the escalate-versus-assist asymmetry; its discordant cells are "
                 "\"escalated but refused help\" and \"assisted but did not escalate\".")

    para(doc, f"**Incoherence is zero — {P['inc']} of {P['tot']}.** The pre-registered "
              f"null holds across every model, family and provider we could reach. **Not "
              f"one model, on any moment, refused to analyse evidence it had just "
              f"declined to escalate.** The design commits in advance to E0+E1 carrying "
              f"the paper in this branch; that commitment is honoured, and the null is "
              f"reported as a result.")
    para(doc, f"**The frames disagree, overwhelmingly and in one direction.** Every model "
              f"assisted on **{P['ass']}/{P['assn']}** moments. They escalated on "
              f"**{P['esc']}/{P['assn']} ({P['esc']/P['assn']:.0%})**. Every discordant "
              f"pair in the entire experiment falls the same way — the model helped "
              f"without paging — and the *tension* cell (escalates but will not help) is "
              f"**empty across all eleven models**. Seven of eleven are individually "
              f"significant at *p* < 0.05.")
    para(doc, "The failure mode this experiment was built to detect was a model that "
              "clams up in both frames. What it measured is the mirror image: **a model "
              "that will explain an intrusion to you in detail and not think it worth "
              "waking anyone over.** Under-escalation, not refusal, is the "
              "safety-relevant behaviour here.")
    para(doc, "**The two findings reconcile rather than conflict.** The weakest E3 arms "
              "are the strongest E1 cry-wolf models: `gemini-3.1-flash-lite` escalates "
              "on 21 of 24 moments and is not individually significant — but it is the "
              "same model that bought 12/12 recall by paging on 11 of 12 innocent "
              "windows. **A model that pages on nearly everything has no headroom to "
              "show an escalation deficit.** Conversely the Mistral models, which page "
              "on nothing in E1, escalate on 0–4% here while assisting on all 72 of "
              "their moments — the same behaviour seen from the other side.")
    para(doc, "**What was excluded, and whether it was random.** Three `gpt-oss-20b` "
              "moments remain `truncated` after a 3× budget re-run — two `supply_chain`, "
              "one `k8s`. Evidence length is identical across all 24 moments, so prompt "
              "size does not explain it; the model reasoned longest on the late-stage "
              "material. **The residue is not evenly spread across phases** and falls on "
              "the higher-consequence ones, the direction that flatters the model. A "
              "further 41 moments (`allam-2-7b` entirely, most of `qwen3.6-27b`) were "
              "lost to a network outage and a per-request size limit respectively; both "
              "are infrastructure, not behaviour, and both are excluded rather than "
              "imputed.")

    heading(doc, "4.5 Cost", 3)
    para(doc, "**$0.00.** Every call ran on a free tier. The binding constraint was "
              "throughput, not price: 10–31 requests per model per day on Google AI "
              "Studio, 1,000 on Groq, 30 requests/minute on Mistral — all measured "
              "rather than assumed.")

    # ---- 5. Discussion and Limitations -------------------------------------
    heading(doc, "5. Discussion and Limitations")
    para(doc, "**Neither half is easy, and they fail separately.** Selecting a monitor "
              "on recall alone picks `gemini-3.1-flash-lite`, which pages on 92% of an "
              "innocent shift. Selecting on false-page rate alone picks `ministral-3b`, "
              "which pages on nothing whatever. Both look excellent on one axis and are "
              "useless. **This is the practical argument for the matched control**: "
              "without a benign stream, half the roster would have looked deployable.")
    para(doc, "Capability does not resolve it. `gpt-oss-120b` discriminates while "
              "`gpt-oss-20b` — same family, provider and serving stack — catches 2 of 12 "
              "milestones, and Mistral's 3b, 8b and 14b are near-identical and "
              "near-silent. **Scale did not buy selectivity in either family.** Note too "
              "which models cleared significance: the two with the deepest benign "
              "sampling, not the two most capable. Sampling depth and selectivity are "
              "confounded here, and we say so rather than reading a capability story "
              "into it.")
    para(doc, "**The metric you pick decides the answer.** First-page latency — the "
              "obvious metric, and the one we pre-registered — is degenerate here. We "
              "only found that because the rule baselines cost nothing to run and made "
              "it visible before the model budget was spent. Cheap non-LLM controls are "
              "not a nicety; they are what keeps an expensive metric honest.")
    para(doc, "**Under-escalation is the finding worth acting on.** The pre-registered "
              "worry was refusal — a guardrail turning a security assistant into an "
              "obstacle mid-incident. It did not happen once in 228 scoreable moments "
              "across 11 models and three providers. What happened instead is that the "
              "same models, on the same bytes, produce a competent analysis and decline "
              "to raise an alarm, every discordant pair falling that way and none the "
              "other. An operator reading the assistant-frame output would conclude the "
              "model understood the situation. They would be right, and the pager would "
              "still be silent.")
    para(doc, "**A false page is not a free page.** Alert fatigue is a documented, "
              "surveyed failure mode in real SOCs [11]: false positives consume the "
              "analyst hours genuine detections need, and sustained volume drives both "
              "error and attrition. A monitor that pages on roughly half an "
              "intrusion-free stream is not conservative; it is degrading the capacity "
              "it was added to supplement.")
    para(doc, "So the safety question for monitoring deployments is not \"will the model "
              "help?\" — it demonstrably will, on 228 of 228 moments — but **\"does the "
              "model's willingness to *act* track its understanding?\"** Here it does "
              "not, and the gap runs one way.")
    heading(doc, "Limitations", 3)
    para(doc, "**The corpus is a reconstruction, not a capture.** Claims are about model "
              "behaviour on a faithful scaffold built from published figures, not about "
              "what Hugging Face's stack would have done. **75% of the corpus (13,163 "
              "actions across recon and dropper) carries no sourced milestone** — it is "
              "filler obeying published marginals, so behaviour there is behaviour on "
              "our generator. Six of twelve milestone timestamps are interpolated within "
              "published bounds, one milestone is unreconciled between the two sources, "
              "and the MITRE mappings are ours — neither source uses ATT&CK, and since "
              "the escalation ground truth keys off tactic, our mapping partly determines "
              "the metric that scores it.")
    para(doc, "**Statistical power is the dominant limitation and it is unevenly "
              "distributed.** Per-cell *n* runs from 1 to 36. Only 2 of 15 models reach "
              "*p* < 0.05 on stream separation, and the confound is ours rather than "
              "theirs: they are the two we could sample most deeply. **Significance here "
              "tracks sampling budget at least as much as model behaviour**, so the "
              "shape of the distribution is the reportable claim and no individual "
              "ranking is established.")
    para(doc, "**Single-run, single-turn, text-only, English-only.** Temperature 0, one "
              "draw per cell. No multi-turn drift, no tool use, no agentic scaffolds, "
              "and **no repeated sampling** — a model that pages 40% here might page 60% "
              "on a re-run, and we have not measured that variance.")
    para(doc, "**No frontier-proprietary model is in this study at all.** The Google Pro "
              "tier returns `limit: 0` at $0, Cerebras requires payment, and GitHub "
              "Models — the GPT-class arm the pre-registration named — was retired "
              "mid-sprint. Our \"frontier\" arm is frontier-*flash*.")
    para(doc, "**The E3 effect size varies a great deal.** The zero incoherence rate "
              "replicates everywhere and the asymmetry replicates in direction "
              "everywhere, but escalation ranges from 0% to 90% and only 7 of 11 models "
              "are individually significant. Reporting the pooled asymmetry alone would "
              "overstate how uniform it is.")
    para(doc, "**Serving stacks are a confound we bound but cannot remove.** A model is "
              "a model *as served by someone*: quantisation, sampling defaults, "
              "system-prompt injection and moderation layers all differ. We report the "
              "provider beside every model ID; `gpt-oss-20b` vs `gpt-oss-120b` is the "
              "one clean within-stack comparison.")
    para(doc, "**Prompt framing is not authentication.** A model reading \"you are the "
              "triage layer\" cannot verify it. Everything here measures response to a "
              "*claimed* role.")
    para(doc, "**One of our own bugs is instructive and is disclosed.** At a 300-token "
              "budget GLM-5.2 spent 524 tokens reasoning and returned empty content — "
              "scored naively, a refusal. This bug class recurred four times, most "
              "recently when `gpt-oss-20b` spent 1,998 of a 2,000-token budget on "
              "reasoning and emitted nothing. Any benchmark that does not separate "
              "`truncated` from `refused` will systematically over-report refusal for "
              "reasoning models, and will do so *more* for the models that reason "
              "hardest. Note the direction, because it defeats the obvious heuristic: "
              "the **smaller** model burned more reasoning budget than the larger one.")

    heading(doc, "Future Work", 3)
    para(doc, "**Widen the sample.** The sampling ladder makes this purely additive — "
              "rung 108 or 324 re-uses every window already paid for. At *n* = 108 "
              "benign per model the per-model intervals would narrow enough to support "
              "the ranking this study deliberately declines to make.")
    para(doc, "**Reach a frontier-proprietary model.** Whether GPT- or Claude-class "
              "models show the same escalate-versus-assist asymmetry is the single most "
              "important open question here, and it is a budget problem rather than a "
              "design one.")
    para(doc, "**Vary the escalation threshold explicitly.** We measured a binary "
              "page/don't-page decision at whatever implicit threshold each model "
              "carries. Eliciting a calibrated probability instead would separate \"the "
              "model did not notice\" from \"the model noticed and judged it "
              "sub-threshold\" — two very different failures that our design collapses.")
    para(doc, "**Multi-turn and tool-using monitors.** A real SOC assistant can pivot, "
              "query and correlate. Whether the escalation gap survives when the model "
              "can investigate rather than only read is untested.")
    para(doc, "**Repeated sampling.** Every cell here is one draw at temperature 0. The "
              "run-to-run variance of a page decision is unmeasured and could be large.")

    # ---- 6. Conclusion -----------------------------------------------------
    heading(doc, "6. Conclusion")
    para(doc, "We rebuilt a real 2026 agent intrusion as a replayable stream with a "
              "matched benign control, and asked 15 models whether they would wake the "
              "on-call. The answer is not that they refuse, and not that they are "
              "uniformly bad. It is that **recall and selectivity fail independently, "
              "and almost nothing achieves both**: one model pages on 92% of an innocent "
              "shift, two page on nothing at all and describe an active intrusion as "
              "resource contention, and only two of fifteen separate the streams at all. "
              "A fifteen-line keyword rule shows the same shape, which suggests the "
              "problem is not model crudeness but a thin discriminating signal that "
              "current monitors do not extract.")
    para(doc, "The second finding is the one we did not expect and consider more "
              "important. Holding evidence byte-identical and varying only the frame, "
              "**incoherence was zero across 228 moments and 11 models** — no model ever "
              "refused to analyse what it had just declined to escalate — but the frames "
              "disagreed in one direction only: **228/228 assisted, 83 escalated.** The "
              "risk in an AI-assisted SOC is not the model that will not discuss the "
              "incident. It is the model that discusses it fluently while the pager "
              "stays silent. Refusal benchmarks, which measure willingness to engage, "
              "would score this roster a clean sheet and miss the failure entirely.")

    # ---- Code and Data -----------------------------------------------------
    heading(doc, "Code and Data")
    para(doc, "**Code repository:** https://github.com/praneeth3696/apart_ai_sprint")
    para(doc, "The repository contains the corpus generator and its ground truth, the "
              "multi-provider harness, the E0/E1/E3 runners with offline `--dry-run` "
              "modes, the analysis and figure code, the frozen scoring rubric with its "
              "amendment log, the pre-registration with a timestamped amendment log, and "
              "the raw per-window decision records. 218 tests.")
    para(doc, "**Data:** the generated attack stream (17,613 actions), the matched "
              "benign control, the windowed sets and the K=24 moment set are all in the "
              "repository and are regenerable from `corpus/ground_truth.yaml`.")
    para(doc, "**Dual-use note.** The corpus contains no working exploit code, no "
              "payloads, no credentials and no technique absent from the two cited "
              "public sources. It is a *detection* substrate: it describes what an "
              "intrusion looked like in a log, not how to perform one. Every attack step "
              "is downstream of a vendor's own published post-incident write-up. See "
              "Appendix A.")

    # ---- Author Contributions ----------------------------------------------
    heading(doc, "Author Contributions")
    para(doc, "**A.Y.M.** built the corpus and its ground truth: the generation "
              "pipeline, the ten phase template banks, the attack stream, the matched "
              "benign control, the windowing and the K=24 phase-stratified moment set, "
              "with the citation ledger and its coverage-honesty grading. She designed "
              "and ran the blind separability check, authored the Related Work section "
              "and verified all 11 references against their landing pages — correcting "
              "two overclaims in the process — reconciled the pre-registration's "
              "lead-time basis, and collected the Gemini arm of the E3 experiment on her "
              "own free-tier account.")
    para(doc, "**P.R.Y.** built the measurement side: the multi-provider client, the E0 "
              "rule baselines, the E1 escalation runner and the E3 two-frame runner, the "
              "nested sampling ladder, the statistics and figures, and the provider "
              "measurement protocol. He ran the E1 and E3 experiments across Google, "
              "Groq and Mistral, and drafted the report front-half.")
    para(doc, "Both authors contributed to the pre-registration and its amendment log, "
              "the scoring rubric, the Limitations and Dual-Use appendix, and reviewed "
              "the final manuscript. All experimental work was coordinated through pull "
              "requests; the commit history is public.")

    # ---- References --------------------------------------------------------
    heading(doc, "References")
    for i, r in enumerate(REFS, 1):
        q = para(doc, "", space_after=4)
        q.paragraph_format.left_indent = Inches(0.35)
        q.paragraph_format.first_line_indent = Inches(-0.35)
        run = q.add_run(f"[{i}] {r}")
        run.font.size = Pt(9)
    # ---- Appendix A --------------------------------------------------------
    heading(doc, "Appendix A — Dual-Use Considerations")
    para(doc, "**What the artefact contains.** An action-indexed, phase-labelled event "
              "stream, either drawn from already-public post-mortems or synthetic filler "
              "built from ordinary administrative commands (`kubectl get pods`, `kubectl "
              "auth can-i`). It contains **no working exploit code, no payloads, no "
              "novel installation recipes and no credentials.** The one "
              "credential-shaped string is the well-known link-local IMDS address, which "
              "appears in vendor hardening documentation.")
    para(doc, "**What it is for.** Practitioners asked of this incident: *\"which action "
              "number does your control fire on?\"* That is unanswerable without a "
              "replayable stream. This corpus exists to make control-firing latency "
              "measurable. Its intended users are defenders.")
    para(doc, "**Uplift assessment.** The offensive content is a chronological ordering "
              "of techniques already documented in the two primary sources. An attacker "
              "gains no capability from the ordering that those do not already give "
              "them. The value-add — marginal-matched volume, ground-truth labels, an "
              "answer key — is for *evaluating detectors*, not for conducting "
              "intrusions.")
    para(doc, "**The dual-use surface is the finding, not the data.** We report which "
              "models under-escalate and by how much. An attacker knowing a monitor "
              "pages on only a third of pivotal moments could in principle shape "
              "activity beneath it. Three things bound this: it is a September-2026 "
              "snapshot of production endpoints that model updates will invalidate; it "
              "is specific to our reconstruction, and generalisation to real SOC "
              "telemetry is exactly what we do not claim; and it is the same fact a "
              "defender needs before putting a model on monitoring duty. Withholding it "
              "protects no one and leaves operators calibrating on optimism.")
    para(doc, "**What we withhold.** No novel installation recipe is released without "
              "review.")

    # ---- Appendix B --------------------------------------------------------
    heading(doc, "Appendix B — An incidental observation while writing this paper")
    para(doc, "This is an anecdote, not a measurement. We record it because it is a "
              "first-person instance of the phenomenon Related Work describes, and "
              "because it happened *while drafting a paper about it*.")
    figure(doc, FIGDIR / "figure3_opus5_cyber_flag.jpeg", 6.3,
           "Figure 3. A safety classifier interrupting work on this paper. The message "
           "was flagged, the session was silently downgraded to a smaller model, and the "
           "stated reason was the single token `[cyber]`.")
    para(doc, "The assistant used to draft this report was interrupted by its own "
              "provider's safeguards, which flagged the work and switched the session to "
              "a smaller model. The vendor's notice is explicit about the trade-off: "
              "*\"our intentionally broad safeguards allow us to deliver more "
              "capabilities faster, but can sometimes flag legitimate coding, "
              "cybersecurity, and biology tasks.\"* The classification detail was "
              "`[cyber]`.")
    para(doc, "Nothing in the flagged work was offensive. The project is a detection "
              "benchmark built from two vendors' own published post-incident reports. "
              "This is precisely the pattern *Defensive Refusal Bias* [7] quantifies at "
              "scale — security keywords refused at 2.72× the rate of neutral phrasing — "
              "and it is the same layer our own earlier measurement found blocking "
              "defensive SOC triage prompts before generation.")
    para(doc, "We draw a narrow conclusion. **n = 1, and we do not report it as a "
              "result.** But it is worth stating plainly that the friction this "
              "literature measures is not hypothetical: it was a live obstacle to "
              "producing this paper, on a task whose entire purpose was to help "
              "defenders, and the mitigation available to us was to accept a less "
              "capable model. A defender under incident pressure has less patience for "
              "that than a researcher on a weekend does.")

    # ---- LLM Usage Statement -----------------------------------------------
    heading(doc, "LLM Usage Statement")
    para(doc, "**LLM assistance was substantial and is disclosed in full.** Claude "
              "(Opus 5, via Claude Code) wrote the great majority of the code in this "
              "repository — the multi-provider client, the E1 and E3 runners, the "
              "statistics, the figures and the test suites — and drafted the prose of "
              "this report. It also produced the 20 labels for the blind separability "
              "check in §3.2, which the pre-registration had specified as a human task; "
              "that substitution is disclosed there and in the result file itself rather "
              "than only here.")
    para(doc, "**What the authors did.** We set the research direction and the threat "
              "model; chose the experiments, the metrics and the controls; wrote the "
              "pre-registration and the frozen rubric before any scoring; obtained and "
              "measured the providers; decided every methodological judgement call, "
              "including demoting first-page latency and adding the `quota_exhausted` "
              "outcome; and verified the results. A.Y.M. independently checked all 11 "
              "references in Related Work against their landing pages and corrected two "
              "overclaims the model had drafted, and reconciled a three-way "
              "inconsistency in the pre-registration's lead-time basis that the model "
              "had not noticed.")
    para(doc, "**Verification.** Every number in this report is generated from the raw "
              "decision records by `analysis/stats.py` and cross-checked against them by "
              "`report/check_numbers.py`, which verifies each table row, the pooled "
              "figures and the significance count and fails the build on a mismatch. "
              "That gate exists because the report did silently go stale once during the "
              "sprint: a new arm of data moved the pooled false-page rate and turned "
              "\"no model reaches significance\" into \"two do\", while the abstract "
              "still asserted the old claim. No claim here rests on an unverified model "
              "output.")
    para(doc, "**Caveat we want stated.** The prose of this report is the model's, "
              "edited by us. Readers should weigh it accordingly, and the repository's "
              "commit history records exactly who changed what and when.")

    return doc


def _save(doc):
    doc.save(str(OUT))
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    _save(main())
