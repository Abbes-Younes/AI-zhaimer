"""Streaming subject loop (phase_1.md §0a, §1).

For each subject: download raw (~590 MB) → preprocess each task → verify the
derivatives exist → delete the raw (unless --keep-raw). Raw is RETAINED on any
failure so the subject can be re-processed without re-downloading. Peak raw on
disk stays ~1.2 GB regardless of total scope.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .download import (
    download_subject,
    load_manifest,
    load_url_map,
    manifest_for_subject,
)
from .paths import (
    RAW_DIR,
    require_free_space,
    ensure_dirs,
)
from .preprocess import PreprocessError, derivative_exists, process_subject_task

log = logging.getLogger("pearl_preproc.pipeline")


def _tasks_for(rows: list[dict]) -> list[str]:
    return sorted({r["task"] for r in rows})


def delete_raw(subject: str) -> None:
    d = RAW_DIR / subject
    if d.exists():
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def process_subject(subject: str, cfg: dict, url_map: dict[str, str],
                    manifest: list[dict], keep_raw: bool = False) -> dict:
    """Streaming loop for one subject. Raw retained on any failure."""
    rows = manifest_for_subject(manifest, subject)
    summary = {"subject": subject, "ok": False, "tasks": [], "raw_retained": False,
               "reason": None, "skipped": False}

    # Resume contract (§1): a valid derivative for every task means this
    # subject is already done — skip it without touching the network or disk.
    tasks = _tasks_for(rows)
    if tasks and all(derivative_exists(subject, t) for t in tasks):
        summary["ok"] = True
        summary["skipped"] = True
        summary["reason"] = "already processed (resume skip)"
        return summary

    dl = download_subject(subject, rows, url_map, cfg)
    if dl["quarantined"]:
        summary["reason"] = f"download quarantined: {dl['errors']}"
        summary["raw_retained"] = True
        return summary

    for task in tasks:
        try:
            metrics = process_subject_task(subject, task, cfg)
            summary["tasks"].append({"task": task, "ok": True, **metrics})
        except PreprocessError as exc:
            summary["tasks"].append({"task": task, "ok": False, "error": str(exc)})
            summary["reason"] = f"preprocess failed on {task}: {exc}"
            break
        except Exception as exc:  # any pipeline failure → retain raw, move on
            summary["tasks"].append({"task": task, "ok": False, "error": repr(exc)})
            summary["reason"] = f"preprocess raised on {task}: {exc!r}"
            break

    if summary["reason"]:
        summary["raw_retained"] = True
        return summary

    # Verify derivatives before deleting the raw.
    tasks_ok = [t["task"] for t in summary["tasks"]]
    missing = [t for t in tasks_ok if not derivative_exists(subject, t)]
    if missing:
        summary["reason"] = f"derivative verification failed for {missing}"
        summary["raw_retained"] = True
        return summary

    summary["ok"] = True
    if not keep_raw:
        delete_raw(subject)
    return summary


def preprocess_all(cfg: dict, subjects: list[str] | None = None) -> dict:
    """Standalone preprocess of already-downloaded raw (no download, no delete)."""
    ensure_dirs()
    manifest = load_manifest()
    all_subjects = sorted({r["subject"] for r in manifest})
    todo = subjects or all_subjects
    todo = [s for s in todo if s in set(all_subjects)]
    results = []
    for s in todo:
        rows = manifest_for_subject(manifest, s)
        tasks = _tasks_for(rows)
        summary = {"subject": s, "ok": True, "tasks": []}
        for task in tasks:
            try:
                summary["tasks"].append(process_subject_task(s, task, cfg))
            except Exception as exc:
                summary["ok"] = False
                summary["reason"] = f"{task}: {exc!r}"
                break
        results.append(summary)
    return {"completed": [r["subject"] for r in results if r["ok"]],
            "failed": [r for r in results if not r["ok"]]}


def run_all(cfg: dict, subjects: list[str] | None = None,
            keep_raw: bool = False, n_workers: int = 2) -> dict:
    """Process every manifest subject through the streaming loop."""
    ensure_dirs()
    require_free_space()
    manifest = load_manifest()
    url_map = load_url_map()

    all_subjects = sorted({r["subject"] for r in manifest})
    todo = subjects or all_subjects
    todo = [s for s in todo if s in set(all_subjects)]
    if not todo:
        return {"subjects": [], "completed": [], "failed": [], "quarantined": []}

    results: list[dict] = []
    if n_workers <= 1:
        for s in todo:
            results.append(process_subject(s, cfg, url_map, manifest, keep_raw))
    else:
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(process_subject, s, cfg, url_map, manifest, keep_raw): s
                for s in todo
            }
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as exc:
                    results.append({"subject": futures[fut], "ok": False,
                                    "reason": f"worker raised: {exc!r}",
                                    "raw_retained": True})

    failed = [r for r in results if not r["ok"]]
    skipped = [r["subject"] for r in results if r.get("skipped")]
    processed = [r["subject"] for r in results if r["ok"] and not r.get("skipped")]
    return {
        "subjects": todo,
        "completed": processed,
        "skipped": skipped,
        "failed": failed,
        "n_completed": len(processed),
        "n_skipped": len(skipped),
        "n_failed": len(failed),
    }
