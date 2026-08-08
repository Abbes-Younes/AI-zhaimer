"""Phase 1 QC report (phase_1.md §3) — verdict-first, self-contained HTML.

The per-group exclusion breakdown is computed ONLY after the exclusion list is
frozen (qc.freeze_exclusions), and only here — this is the single place Phase 1
reads the cohort definition, for reporting, not for threshold-setting.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import yaml

from .paths import (
    QC_DIR,
    REPORTS_DIR,
    CONFIG_DIR,
    get_run_id,
)

# Post-freeze reporting only (phase_1.md §3): the client's group lists.
# report_qc is the single sanctioned place Phase 1 reads labels — the exclusion
# list itself was frozen from QC metrics before any label was joined.
_CLIENT_GROUPS_YAML = CONFIG_DIR / "client_groups.yaml"

_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1100px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; }
h1 { color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }
h2 { color: #16213e; margin-top: 30px; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: 5px 8px; text-align: left; }
th { background-color: #16213e; color: white; }
tr:nth-child(even) { background-color: #f7f7f7; }
.verdict-pass { color: #27ae60; font-weight: bold; }
.verdict-warn { color: #f39c12; font-weight: bold; }
.verdict-fail { color: #e74c3c; font-weight: bold; }
.box { background: #f8f9fa; border-left: 4px solid #16213e; padding: 15px; margin: 15px 0; }
.box-stop { border-left-color: #e74c3c; background: #fdf2f2; }
.box-proceed { border-left-color: #27ae60; background: #f0faf0; }
pre { background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; }
"""


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _load_cohort() -> dict[str, dict]:
    """subject → {group, ...} from client_groups.yaml (post-freeze only)."""
    if not _CLIENT_GROUPS_YAML.exists():
        return {}
    cfg = yaml.safe_load(_CLIENT_GROUPS_YAML.read_text(encoding="utf-8")) or {}
    out = {}
    for group, info in (cfg.get("groups") or {}).items():
        for subj in (info or {}).get("subjects", []):
            out[subj] = {"group": group, "final_include": True}
    return out


def _task_is(task: str, name: str) -> bool:
    """True if *task* denotes *name* (sidecars say "rest", config says "task-rest")."""
    return task == name or task == f"task-{name}"


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_false(value) -> bool:
    """Accept real bools and the "True"/"False" strings CSV round-trips
    produce — comparing only against the string silently breaks if a caller
    ever passes rows straight from qc.build_qc_table() instead of a CSV."""
    if isinstance(value, bool):
        return value is False
    return str(value).strip().lower() == "false"


def _is_true(value) -> bool:
    if isinstance(value, bool):
        return value is True
    return str(value).strip().lower() == "true"


def per_group_exclusion_counts(excluded: list[dict], cohort: dict[str, dict]) -> dict:
    """Count excluded subjects per group — run AFTER the freeze."""
    counts: dict[str, dict] = {}
    for row in excluded:
        info = cohort.get(row["subject"], {})
        g = info.get("group") or "not-in-cohort"
        c = counts.setdefault(g, {"group": g, "n_excluded": 0,
                                  "subjects": []})
        c["n_excluded"] += 1
        c["subjects"].append(row["subject"])
    return counts


def generate(qc_summary: dict, cfg: dict) -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics = _read_csv(QC_DIR / "qc_metrics.csv")
    excluded = _read_csv(QC_DIR / "excluded_subjects.csv")
    cohort = _load_cohort()
    group_counts = per_group_exclusion_counts(excluded, cohort)

    n_subjects = len({r["subject"] for r in metrics})
    n_rows = len(metrics)
    n_fail = sum(1 for r in metrics if r["verdict"] == "fail")
    n_warn = sum(1 for r in metrics if r["verdict"] == "warn")
    no_alpha = [r["subject"] for r in metrics
                if _is_false(r.get("alpha_present"))
                and _task_is(r.get("task") or "", "rest")]
    # Borderline rest alpha (1.5 dB to the prominence bar): weak but plausibly
    # real peaks. Reported as a Phase 2 method-viability finding, NOT an
    # exclusion reason (client decision 2026-08-06).
    min_prom = _to_float(cfg.get("iaf", {}).get("min_peak_prominence_db", 3.0))
    borderline_alpha = sorted({
        r["subject"] for r in metrics
        if _task_is(r.get("task") or "", "rest")
        and _is_false(r.get("alpha_present"))
        and 1.5 <= _to_float(r.get("alpha_peak_height_db")) < min_prom
    })

    # Escalation checks (phase_1.md §8)
    escalation = []
    if len(excluded) > 5:
        escalation.append(f"{len(excluded)} subjects excluded (> 5 threshold)")
    max_group_frac = 0.0
    if group_counts:
        tot = sum(c["n_excluded"] for c in group_counts.values())
        max_group_frac = max(c["n_excluded"] / max(tot, 1) for c in group_counts.values())
    if max_group_frac > 0.8 and len(excluded) >= 3:
        escalation.append(f"exclusions concentrate in one group ({max_group_frac:.0%})")
    if no_alpha and len(no_alpha) / max(n_subjects, 1) > 0.3:
        escalation.append(f"{len(no_alpha)} rest subjects lack an alpha peak "
                          f"({len(no_alpha) / max(n_subjects, 1):.0%} of subjects)")
    if n_subjects and (n_subjects - len(excluded)) < 70:
        escalation.append(
            f"only {n_subjects - len(excluded)} subjects survive (< 70) for the "
            f"primary target framing")

    verdict = "ESCALATE" if escalation else "PROCEED"

    rows_html = []
    for r in metrics:
        cls = f"verdict-{r['verdict']}"
        harm = "&#10003;" if _is_true(r.get("fifth_harmonic_collision")) else ""
        rows_html.append(
            f"<tr><td>{r['subject']}</td><td>{r['task']}</td>"
            f"<td>{r['duration_s']}</td><td>{r['expected_duration_s']}</td>"
            f"<td>{r['n_bad_channels']}</td><td>{r['bad_channels']}</td>"
            f"<td>{r['occipital_bads']}</td><td>{r['n_ica_components']}/{r['n_ica_removed']}</td>"
            f"<td>{r['ica_removed_labels']}</td><td>{r['iaf_hz']}</td>"
            f"<td>{r['alpha_peak_height_db']}</td><td>{harm}</td>"
            f"<td>{r['line_noise_index_before']}→{r['line_noise_index_after']}</td>"
            f"<td>{r['artifact_frac']}</td>"
            f"<td class=\"{cls}\">{r['verdict'].upper()}</td><td>{r['flags']}</td></tr>")

    excluded_rows = "".join(
        f"<tr><td>{e['subject']}</td><td>{e['reason']}</td><td>{e['frozen_at'][:19]}</td></tr>"
        for e in excluded) or "<tr><td colspan=3>none</td></tr>"

    group_rows = ""
    if group_counts:
        tot = sum(c["n_excluded"] for c in group_counts.values())
        group_rows = "".join(
            f"<tr><td>{c['group']}</td><td>{c['n_excluded']}</td>"
            f"<td>{c['n_excluded'] / max(tot, 1):.0%}</td>"
            f"<td>{', '.join(c['subjects'])}</td></tr>" for c in group_counts.values())
    else:
        group_rows = "<tr><td colspan=4>no exclusions — no per-group counts needed</td></tr>"

    esc_rows = "".join(f"<li>{e}</li>" for e in escalation) or "<li>none</li>"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Phase 1 QC — PEARL-Neuro ds004796</title>
<style>{_CSS}</style></head><body>
<h1>Phase 1 QC Report — PEARL-Neuro (ds004796)</h1>
<p><strong>Generated:</strong> {date.today().isoformat()} | <strong>Run:</strong> {get_run_id() or 'unmanaged'}</p>
<div class="box box-{'stop' if verdict == 'ESCALATE' else 'proceed'}">
<h2>Verdict: {verdict}</h2>
<p>{len(excluded)} subject(s) excluded on QC grounds (frozen before any label was
joined); {n_rows} (subject, task) rows processed across {n_subjects} subjects
({n_fail} fail, {n_warn} warn).</p>
<ul>{esc_rows}</ul>
</div>

<h2>1. Per-group exclusion counts (computed AFTER the freeze)</h2>
<table><tr><th>Group</th><th>Excluded</th><th>Share</th><th>Subjects</th></tr>{group_rows}</table>
<p>These counts are reported only to detect uneven QC attrition; thresholds were
not revised as a result (phase_1.md §3).</p>

<h2>2. Excluded subjects (frozen)</h2>
<table><tr><th>Subject</th><th>Reason</th><th>Frozen at</th></tr>{excluded_rows}</table>

<h2>3. QC metrics (per subject, task)</h2>
<table>
<tr><th>Subject</th><th>Task</th><th>Dur s</th><th>Exp s</th><th>Bad ch</th>
<th>Bad names</th><th>Occ bads</th><th>ICA removed</th><th>ICA labels</th>
<th>IAF Hz</th><th>Alpha dB</th><th>5th-harm</th><th>50 Hz index before→after</th>
<th>Artifact frac</th><th>Verdict</th><th>Flags</th></tr>
{''.join(rows_html)}</table>

<h2>4. Rest alpha findings (Phase 2 method-viability, phase_1.md §8)</h2>
<p><strong>No identifiable alpha peak (&lt; 1.5 dB above the 1/f baseline):</strong>
{', '.join(sorted(set(no_alpha))) or 'none'}</p>
<p><strong>Borderline (1.5–{min_prom:.1f} dB — reported, not excluded):</strong>
{', '.join(borderline_alpha) or 'none'}</p>
<p>Cycle-level (pitch-synchronous) analysis in Phase 2 rests on alpha being
present in rest; subjects without an identifiable peak cannot support it. The
borderline list is a finding for the Phase 2 method decision, not a QC revision.</p>

<h2>5. Reproduction</h2>
<pre>python -m pearl_preproc.cli run-all</pre>
<p>Exclusion list: <code>data/derivatives/preproc/qc/excluded_subjects.csv</code> —
consumed as given by Phase 2. Verdicts use fixed thresholds from
<code>config/preproc.yaml</code>.</p>
</body></html>"""
    out = REPORTS_DIR / "phase1_qc.html"
    out.write_text(html, encoding="utf-8")
    return {
        "html_path": str(out),
        "verdict": verdict,
        "n_excluded": len(excluded),
        "n_rows": n_rows,
        "n_subjects": n_subjects,
        "n_alpha_missing_rest": len(no_alpha),
        "n_alpha_borderline_rest": len(borderline_alpha),
        "group_counts": group_counts,
        "escalation": escalation,
    }
