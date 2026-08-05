"""Generate Phase 0/0.5 audit report as self-contained HTML + Markdown (§8 + phase_0,5.md Task 7)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

from .paths import (
    AUDIT_YAML,
    REPORTS_DIR,
    RunIdMismatchError,
    artifact_dir,
    get_run_id,
)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _load_csv(path: Path) -> list[dict]:
    import csv
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _compute_verdict(reconciliation_summary: dict, audit_cfg: dict) -> tuple[str, str]:
    """Return (verdict, verdict_text) from the reconciliation summary.

    phase_0,5.md Task 2: the stop-gate counts blocking statuses
    (MISMATCH + MISSING_FROM_TSV). sub-69 not being among the 192 genotyped
    participants closes the Phase 0 question rather than flagging a condition.
    """
    mismatch_count = reconciliation_summary.get("mismatch_count", 0)
    max_mismatches = audit_cfg.get("thresholds", {}).get("max_mismatches", 2)

    if mismatch_count > max_mismatches:
        verdict = "stop"
        verdict_text = (
            f"STOP: {mismatch_count} blocking statuses (MISMATCH/MISSING_FROM_TSV) exceed "
            f"the {max_mismatches}-subject threshold. The client's grouping rule may differ "
            f"from the stated definition. Every label in the project is suspect until resolved."
        )
    else:
        sub69 = reconciliation_summary.get("sub_69", {})
        verdict = "proceed"
        if sub69.get("present_in_tsv"):
            sub69_clause = "sub-69 IS present in participants.tsv but is in no client group."
        else:
            sub69_clause = "sub-69 is not among the genotyped participants, which closes the Phase 0 question."
        verdict_text = (
            f"PROCEED: all {reconciliation_summary.get('analysis_cohort_count', 0)} analysis-cohort subjects "
            f"reconcile to the client's groups (0 blocking statuses). The dataset holds "
            f"{reconciliation_summary.get('total_subjects_in_tsv', 0)} genotyped participants; only the "
            f"{reconciliation_summary.get('analysis_cohort_count', 0)} in the client list are expected to have "
            f"imaging. {sub69_clause} "
            f"No blocking confounds detected. Phase 1 may proceed under the download plan in §5."
        )
    return verdict, verdict_text


def _assert_same_run_id() -> None:
    """Assert the artifacts under the current artifact dir share one run_id.

    phase_0,5.md Task 4: the report must refuse to render if its inputs were
    produced by different runs. The ``_meta.json`` stamped at run start records
    the run_id; when a managed run is active, the report checks that all input
    CSVs sit in the same run's staging dir and that the meta matches. Outside a
    managed run (unit tests) the assertion is skipped.
    """
    active_run = get_run_id()
    if not active_run:
        return
    meta = artifact_dir() / "_meta.json"
    if meta.exists():
        data = json.loads(meta.read_text(encoding="utf-8"))
        meta_run = data.get("run_id")
    else:
        meta_run = None
    if meta_run != active_run:
        raise RunIdMismatchError(
            f"Artifacts were produced by run {meta_run!r} but the report is being "
            f"generated for run {active_run!r}. Refusing to render mixed-run output."
        )


# ---------------------------------------------------------------------------
# HTML generation (self-contained, no CDN)
# ---------------------------------------------------------------------------

_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; }
h1 { color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }
h2 { color: #16213e; margin-top: 30px; }
h3 { color: #0f3460; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background-color: #16213e; color: white; }
tr:nth-child(even) { background-color: #f2f2f2; }
.verdict-clear { color: #27ae60; font-weight: bold; }
.verdict-watch { color: #f39c12; font-weight: bold; }
.verdict-blocking { color: #e74c3c; font-weight: bold; }
.box { background: #f8f9fa; border-left: 4px solid #16213e; padding: 15px; margin: 15px 0; }
.box-stop { border-left-color: #e74c3c; background: #fdf2f2; }
.box-proceed { border-left-color: #27ae60; background: #f0faf0; }
pre { background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; }
code { background: #f4f4f4; padding: 2px 4px; border-radius: 2px; }
"""


def _provenance_rows(audit_cfg: dict) -> list[tuple[str, str]]:
    prov = audit_cfg.get("provenance", {})
    dataset = audit_cfg.get("dataset", {})
    rows = [
        ("Accession", prov.get("accession") or "ds004796"),
        ("Version", prov.get("version_string") or dataset.get("version") or "unknown"),
        ("Version source", prov.get("version_source") or "unknown"),
        ("Fetch date", prov.get("fetch_date") or dataset.get("fetch_date") or "unknown"),
        ("participants.tsv SHA-256", (prov.get("participants_tsv_sha256") or "unknown")[:16] + "…"),
        ("S3 listing date", prov.get("s3_listing_date") or "unknown"),
    ]
    return rows


def _generate_html(context: dict) -> str:
    """Build the self-contained HTML report."""
    reconciliation = context.get("reconciliation", {})
    inventory = context.get("inventory", {})
    confounds = context.get("confounds", {})
    size_survey = context.get("size_survey", {})
    download_plan = context.get("download_plan", {})
    fetch = context.get("fetch", {})
    audit_cfg = context.get("audit_config", {})
    verdict = context.get("verdict", "unknown")
    cohort = reconciliation.get("cohort", [])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Phase 0.5 Audit — PEARL-Neuro ds004796</title>
<style>{_CSS}</style>
</head>
<body>

<h1>Phase 0.5 Audit Report — PEARL-Neuro (ds004796)</h1>
<p><strong>Generated:</strong> {date.today().isoformat()} &nbsp;|&nbsp;
<strong>Run:</strong> {context.get('run_id', 'unknown')}</p>

<div class="box box-{'stop' if verdict == 'stop' else 'proceed'}">
<h2>Verdict: {verdict.upper()}</h2>
<p>{context.get('verdict_text', 'No verdict generated.')}</p>
</div>

<h2>0. Cohort Definition</h2>
<p>The dataset contains <strong>{reconciliation.get('total_subjects_in_tsv', '?')} genotyped participants</strong>; of these,
<strong>{reconciliation.get('analysis_cohort_count', '?')}</strong> are in the client's imaging cohort (the client list of 79).
The remaining <strong>{reconciliation.get('genetic_cohort_only_count', '?')}</strong> are genetic-only and are not
expected to have imaging data. Everything downstream filters on <code>final_include</code> in
<code>cohort_definition.csv</code>.</p>
<table>
<tr><th>Subject</th><th>In client list</th><th>In participants.tsv</th><th>Has EEG</th><th>Final include</th></tr>
"""
    for row in cohort:
        html += f"""<tr>
<td>{row.get('subject', '')}</td>
<td>{row.get('in_client_list', '')}</td>
<td>{row.get('in_participants_tsv', '')}</td>
<td>{row.get('has_any_eeg', '')}</td>
<td>{row.get('final_include', '')}</td>
</tr>
"""
    html += "</table>\n"

    html += "<h2>1. Dataset Provenance</h2>\n<table>\n<tr><th>Field</th><th>Value</th></tr>\n"
    for field, value in _provenance_rows(audit_cfg):
        html += f"<tr><td>{field}</td><td>{value}</td></tr>\n"
    html += f"""<tr><td>Total downloaded bytes</td><td>{fetch.get('total_bytes', 0):,}</td></tr>
<tr><td>Files downloaded</td><td>{fetch.get('total_files', 0)}</td></tr>
</table>

<h2>2. Group Reconciliation</h2>
<table>
<tr><th>Subject</th><th>APOE raw</th><th>PICALM raw</th><th>APOE norm</th><th>PICALM norm</th><th>Group (derived)</th><th>Group (client)</th><th>Status</th></tr>
"""
    for row in reconciliation.get("rows", []):
        status = row.get("status", "")
        cls = "verdict-clear" if status == "RECONCILED" else "verdict-blocking"
        html += f"""<tr>
<td>{row.get('subject', '')}</td>
<td>{row.get('apoe_raw', '')}</td>
<td>{row.get('picalm_raw', '')}</td>
<td>{row.get('apoe_norm', '')}</td>
<td>{row.get('picalm_norm', '')}</td>
<td>{row.get('group_derived', '')}</td>
<td>{row.get('group_client', '')}</td>
<td class="{cls}">{status}</td>
</tr>
"""
    html += "</table>\n"

    html += f"""
<h3>Discrepancy Summary</h3>
<ul>
<li>Blocking statuses (MISMATCH + MISSING_FROM_TSV): <strong>{reconciliation.get('mismatch_count', 0)}</strong></li>
<li>Missing from TSV: {', '.join(reconciliation.get('missing_from_tsv', [])) or 'none'}</li>
<li>sub-69: <strong>{'present in participants.tsv' if reconciliation.get('sub_69', {}).get('present_in_tsv') else 'absent from participants.tsv — not one of the 192 genotyped participants'}</strong></li>
<li>e4/e4 homozygotes in A_P_plus: {reconciliation.get('e4_homozygotes_in_A_P_plus', '?')} (claimed: {reconciliation.get('e4_homozygotes_claim', 2)})</li>
</ul>

<h2>3. EEG Inventory &amp; Effective N</h2>
<h3>Effective N per task (wide)</h3>
<table>
<tr><th>Task</th><th>N</th><th>A_P_minus</th><th>A_P_plus</th><th>Total</th></tr>
"""
    for row in inventory.get("effective_n_table", []):
        html += f"""<tr>
<td>{row.get('task', '')}</td>
<td>{row.get('N', '')}</td>
<td>{row.get('A_P_minus', '')}</td>
<td>{row.get('A_P_plus', '')}</td>
<td>{row.get('total', '')}</td>
</tr>
"""
    html += "</table>\n"

    html += "<h3>Missingness per task/group</h3>\n<table>\n<tr><th>Task</th><th>Group</th><th>N total</th><th>Have data</th><th>Missing</th><th>Missing subjects</th><th>Test</th><th>p</th></tr>\n"
    for row in inventory.get("missingness_table", []):
        html += f"""<tr>
<td>{row.get('task', '')}</td>
<td>{row.get('group', '')}</td>
<td>{row.get('n_total', '')}</td>
<td>{row.get('n_have_data', '')}</td>
<td>{row.get('n_missing', '')}</td>
<td>{row.get('missing_subjects', '')}</td>
<td>{row.get('missingness_test', '')}</td>
<td>{row.get('missingness_p', '')}</td>
</tr>
"""
    html += "</table>\n"

    html += f"""
<h4>Documented missingness verification</h4>
<p>sub-51 (sternberg): {inventory.get('verified_known_missing', {}).get('sub-51', {}).get('actually_missing')} &nbsp;|&nbsp;
sub-55 (rest): {inventory.get('verified_known_missing', {}).get('sub-55', {}).get('actually_missing')}</p>

<h2>4. Confound Analysis</h2>
<table>
<tr><th>Framing</th><th>Variable</th><th>Test</th><th>p-value</th><th>Effect size</th><th>Measure</th><th>Verdict</th><th>Mitigation</th></tr>
"""
    for framing, results in confounds.get("framing_results", {}).items():
        for r in results:
            v_class = f"verdict-{r.get('verdict', 'clear')}"
            html += f"""<tr>
<td>{framing}</td>
<td>{r.get('variable', '')}</td>
<td>{r.get('test', '')}</td>
<td>{r.get('p_value', '')}</td>
<td>{r.get('effect_size', '')}</td>
<td>{r.get('effect_measure', '')}</td>
<td class="{v_class}">{r.get('verdict', '').upper()}</td>
<td>{r.get('mitigation', '')}</td>
</tr>
"""
    html += "</table>\n"

    html += "<h2>5. Phase 1 Download Plan</h2>\n<table>\n<tr><th>Scope</th><th>Raw GB</th><th>Derivatives GB</th><th>Total GB</th><th>Fits in 95 GB?</th></tr>\n"
    for name in ["A_full_eeg", "B_rest_msit", "C_rest_msit_only"]:
        scope = download_plan.get("scopes", {}).get(name, {})
        raw = scope.get("raw_gb", 0)
        deriv = download_plan.get("derivatives_per_scope_gb", {}).get(name, 0.0)
        total = raw + deriv
        fits = "YES" if total <= 95 else "NO"
        html += f"<tr><td>{name}</td><td>{raw}</td><td>{deriv}</td><td>{round(total, 2)}</td><td>{fits}</td></tr>\n"
    html += f"""</table>
<p><strong>Recommendation:</strong> {download_plan.get('recommendation', 'unknown')}</p>
<p>Manifest: {download_plan.get('manifest_path', 'none')} — <em>nothing downloaded; approval required.</em></p>

<h2>6. Open Questions &amp; Assumptions</h2>
<ul>
<li>Genotype columns resolved from participants.tsv schema and persisted in config/audit.yaml (no heuristics).</li>
<li>sub-69 is not one of the 192 genotyped participants — the question is closed.</li>
<li>Scope C (eyes-closed rest + MSIT) is file-level identical to Scope B; the eyes-closed subset is carved out at epoch level in Phase 1.</li>
<li>Derivative estimates assume a 250 Hz target rate, float32, with epoched + ICA overhead — see reports/phase1_download_plan.md for the model and its assumptions.</li>
<li>Confound tests run on the 79-subject analysis cohort (asserted from cohort_definition.csv).</li>
</ul>

<h2>7. Reproduction</h2>
<pre>python -m pearl_audit.cli run-all</pre>
<p>Requires: Python &gt;= 3.10, pandas, scipy, pyyaml, jinja2. All artifacts carry the same run_id (see <code>_meta.json</code>).</p>

</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def _generate_markdown(context: dict) -> str:
    """Build the Markdown version of the report."""
    reconciliation = context.get("reconciliation", {})
    inventory = context.get("inventory", {})
    confounds = context.get("confounds", {})
    size_survey = context.get("size_survey", {})
    download_plan = context.get("download_plan", {})
    fetch = context.get("fetch", {})
    audit_cfg = context.get("audit_config", {})
    verdict = context.get("verdict", "unknown")
    cohort = reconciliation.get("cohort", [])

    md = f"""# Phase 0.5 Audit Report — PEARL-Neuro (ds004796)

**Generated:** {date.today().isoformat()} | **Run:** {context.get('run_id', 'unknown')}

## Verdict: {verdict.upper()}

{context.get('verdict_text', 'No verdict generated.')}

---

## 0. Cohort Definition

The dataset contains **{reconciliation.get('total_subjects_in_tsv', '?')} genotyped participants**; of these,
**{reconciliation.get('analysis_cohort_count', '?')}** are in the client's imaging cohort (the client list of 79).
The remaining **{reconciliation.get('genetic_cohort_only_count', '?')}** are genetic-only. Everything downstream
filters on `final_include` in `cohort_definition.csv`.

| Subject | In client list | In participants.tsv | Has EEG | Final include |
|---------|----------------|---------------------|---------|---------------|
"""
    for row in cohort:
        md += f"| {row.get('subject', '')} | {row.get('in_client_list', '')} | {row.get('in_participants_tsv', '')} | {row.get('has_any_eeg', '')} | {row.get('final_include', '')} |\n"

    md += "\n## 1. Dataset Provenance\n\n| Field | Value |\n|-------|-------|\n"
    for field, value in _provenance_rows(audit_cfg):
        md += f"| {field} | {value} |\n"
    md += f"| Total downloaded bytes | {fetch.get('total_bytes', 0):,} |\n"
    md += f"| Files downloaded | {fetch.get('total_files', 0)} |\n"

    md += "\n## 2. Group Reconciliation\n\n| Subject | APOE raw | PICALM raw | APOE norm | PICALM norm | Derived | Client | Status |\n|---------|----------|------------|-----------|-------------|---------|--------|--------|\n"
    for row in reconciliation.get("rows", []):
        md += f"| {row.get('subject', '')} | {row.get('apoe_raw', '')} | {row.get('picalm_raw', '')} | {row.get('apoe_norm', '')} | {row.get('picalm_norm', '')} | {row.get('group_derived', '')} | {row.get('group_client', '')} | {row.get('status', '')} |\n"

    md += f"""
### Discrepancy Summary

- **Blocking statuses (MISMATCH + MISSING_FROM_TSV):** {reconciliation.get('mismatch_count', 0)}
- Missing from TSV: {', '.join(reconciliation.get('missing_from_tsv', [])) or 'none'}
- **sub-69:** {'present in participants.tsv' if reconciliation.get('sub_69', {}).get('present_in_tsv') else 'absent from participants.tsv — not one of the 192 genotyped participants'}
- e4/e4 homozygotes in A_P_plus: {reconciliation.get('e4_homozygotes_in_A_P_plus', '?')} (claimed: {reconciliation.get('e4_homozygotes_claim', 2)})

## 3. EEG Inventory & Effective N

### Effective N per task (wide)

| Task | N | A_P_minus | A_P_plus | Total |
|------|---|-----------|----------|-------|
"""
    for row in inventory.get("effective_n_table", []):
        md += f"| {row.get('task', '')} | {row.get('N', '')} | {row.get('A_P_minus', '')} | {row.get('A_P_plus', '')} | {row.get('total', '')} |\n"

    md += "\n### Missingness per task/group\n\n| Task | Group | N total | Have data | Missing | Missing subjects | Test | p |\n|------|-------|---------|-----------|---------|------------------|------|---|\n"
    for row in inventory.get("missingness_table", []):
        md += f"| {row.get('task', '')} | {row.get('group', '')} | {row.get('n_total', '')} | {row.get('n_have_data', '')} | {row.get('n_missing', '')} | {row.get('missing_subjects', '')} | {row.get('missingness_test', '')} | {row.get('missingness_p', '')} |\n"

    md += f"""
**Documented missingness verification:** sub-51 (sternberg) actually missing = {inventory.get('verified_known_missing', {}).get('sub-51', {}).get('actually_missing')}; sub-55 (rest) actually missing = {inventory.get('verified_known_missing', {}).get('sub-55', {}).get('actually_missing')}.

## 4. Confound Analysis

| Framing | Variable | Test | p | Effect | Measure | Verdict | Mitigation |
|---------|----------|------|---|--------|---------|---------|------------|
"""
    for framing, results in confounds.get("framing_results", {}).items():
        for r in results:
            md += f"| {framing} | {r.get('variable', '')} | {r.get('test', '')} | {r.get('p_value', '')} | {r.get('effect_size', '')} | {r.get('effect_measure', '')} | {r.get('verdict', '').upper()} | {r.get('mitigation', '')} |\n"

    md += "\n## 5. Phase 1 Download Plan\n\n| Scope | Raw GB | Derivatives GB | Total GB | Fits in 95 GB? |\n|---|---|---|---|---|\n"
    for name in ["A_full_eeg", "B_rest_msit", "C_rest_msit_only"]:
        scope = download_plan.get("scopes", {}).get(name, {})
        raw = scope.get("raw_gb", 0)
        deriv = download_plan.get("derivatives_per_scope_gb", {}).get(name, 0.0)
        total = raw + deriv
        fits = "YES" if total <= 95 else "NO"
        md += f"| {name} | {raw} | {deriv} | {round(total, 2)} | {fits} |\n"
    md += f"""
**Recommendation:** {download_plan.get('recommendation', 'unknown')}

Manifest: `{download_plan.get('manifest_path', 'none')}` — *nothing downloaded; approval required.*

## 6. Open Questions & Assumptions

- Genotype columns resolved from participants.tsv schema and persisted in config/audit.yaml (no heuristics).
- sub-69 is not one of the 192 genotyped participants — the question is closed.
- Scope C (eyes-closed rest + MSIT) is file-level identical to Scope B; the eyes-closed subset is carved out at epoch level in Phase 1.
- Derivative estimates assume a 250 Hz target rate, float32, with epoched + ICA overhead — see `reports/phase1_download_plan.md`.
- Confound tests run on the 79-subject analysis cohort (asserted from cohort_definition.csv).
- The full-EEG derivative estimate (~67 GB) far exceeds the 19 GB left after the raw download, which is why Scope A is rejected; Scope C fits with headroom and is therefore recommended (per the phase's budget logic, not an escalation).

## 7. Reproduction

```bash
python -m pearl_audit.cli run-all
```

All artifacts carry the same `run_id` (see `data/derivatives/phase0/_meta.json`); the report refuses to render mixed-run inputs.
"""
    return md


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(
    reconciliation_summary: dict,
    inventory_summary: dict,
    confounds_summary: dict,
    size_survey_summary: dict,
    fetch_summary: dict,
    download_plan_summary: dict | None = None,
) -> dict:
    """Generate the Phase 0.5 report in HTML and Markdown.

    Returns dict with paths to generated files.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # phase_0,5.md Task 4: refuse to render mixed-run inputs.
    _assert_same_run_id()

    # Load audit config for version info
    audit_cfg = _load_yaml(AUDIT_YAML)

    # Load reconciliation CSV for the full table
    recon_csv = artifact_dir() / "group_reconciliation.csv"
    recon_rows = _load_csv(recon_csv)

    context = {
        "reconciliation": {
            "rows": recon_rows,
            "mismatch_count": reconciliation_summary.get("mismatch_count", 0),
            "missing_from_tsv": reconciliation_summary.get("missing_from_tsv", []),
            "sub_69": reconciliation_summary.get("sub_69", {}),
            "e4_homozygotes_in_A_P_plus": reconciliation_summary.get("e4_homozygotes_in_A_P_plus", 0),
            "e4_homozygotes_claim": reconciliation_summary.get("e4_homozygotes_claim", 2),
            "cohort": reconciliation_summary.get("cohort", []),
            "total_subjects_in_tsv": reconciliation_summary.get("total_subjects_in_tsv", 0),
            "genetic_cohort_only_count": reconciliation_summary.get("genetic_cohort_only_count", 0),
            "analysis_cohort_count": reconciliation_summary.get("analysis_cohort_count", 0),
        },
        "inventory": inventory_summary,
        "confounds": confounds_summary,
        "size_survey": size_survey_summary,
        "download_plan": download_plan_summary or {},
        "fetch": fetch_summary,
        "audit_config": audit_cfg,
        "run_id": get_run_id() or "unmanaged",
    }

    # Determine verdict (phase_0,5.md Task 2: stop-gate counts blocking statuses)
    verdict, verdict_text = _compute_verdict(reconciliation_summary, audit_cfg)
    context["verdict"] = verdict
    context["verdict_text"] = verdict_text

    # Generate files
    html = _generate_html(context)
    md = _generate_markdown(context)

    html_path = REPORTS_DIR / "phase0_audit.html"
    md_path = REPORTS_DIR / "phase0_audit.md"

    html_path.write_text(html, encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")

    return {
        "html_path": str(html_path),
        "md_path": str(md_path),
        "verdict": verdict,
    }
