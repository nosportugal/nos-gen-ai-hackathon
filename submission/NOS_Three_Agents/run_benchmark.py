"""Bounded comparison runner for agents A, B and C.

Usage (workspace root, inside the virtual environment):

    python -I run_benchmark.py --freeze            # write freeze manifest
    python -I run_benchmark.py --mode mock         # code-path check only
    python -I run_benchmark.py --mode live         # 3 trials x (1+2+1)

A live benchmark needs 12 inference requests for three trials. It is
refused, before any request is sent, when: the freeze manifest does not
match the current files; no API key is configured; the model cannot be
reached or does not support generateContent; or the remaining global
budget (24 requests for the whole task, failures and retries included)
cannot cover the planned trials. Prompts and settings are never changed
between trials, and every trial is kept, failures included.

Mock results are written to evaluation/mock_benchmark_*; live results to
evaluation/benchmark_*. A blocked live attempt writes NOT_RUN rows, never
invented results.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents import REGISTRY, load_agent  # noqa: E402
from evaluation.evaluate_runs import evaluate  # noqa: E402
from shared import artifacts, config, freeze  # noqa: E402
from shared.runner import NoCredentials, build_context  # noqa: E402

BENCH_DIR = config.RUNS_DIR / "_benchmarks"
EVAL_DIR = config.ROOT / "evaluation"
# Errors that the same request would hit again on every repeat.
SYSTEMIC = ("BAD_REQUEST", "ACCESS_DENIED", "MODEL_NOT_FOUND",
            "BUDGET_EXHAUSTED")


def calls_per_trial(agent_ids) -> int:
    total = 0
    for agent_id in agent_ids:
        folder = Path(load_agent(agent_id).__file__).parent
        cfg = config.load_json(folder / "config.json")
        total += cfg["inference_calls_per_run"]
    return total


def blocked_index(bench_id, mode, agent_ids, trials, reason) -> dict:
    return {
        "benchmark_id": bench_id, "mode": mode,
        "started_utc": artifacts.utc_now(), "blocked": reason,
        "runs": [
            {"agent": a, "trial": t, "mode": mode, "status": "NOT_RUN",
             "failure_reason": "BLOCKED: " + reason}
            for t in range(1, trials + 1) for a in agent_ids
        ],
    }


def write_outputs(index: dict) -> None:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    index_path = BENCH_DIR / f"{index['benchmark_id']}.json"
    config.dump_json(index_path, index)
    stem = "benchmark" if index["mode"] == "LIVE" else "mock_benchmark"
    out_csv = EVAL_DIR / f"{stem}_results.csv"
    if index.get("blocked") and out_csv.exists():
        head = out_csv.read_text(encoding="utf-8").splitlines()[1:2]
        if head and ",NOT_RUN," not in head[0]:
            # Never replace real results with NOT_RUN placeholders.
            out_csv = EVAL_DIR / f"{stem}_results_{index['benchmark_id']}.csv"
    out_md = out_csv.with_name(out_csv.stem.replace("_results", "_tables")
                               + ".md")
    evaluate(index, out_csv, out_md)
    print("index:  ", config.rel(index_path))
    print("results:", config.rel(out_csv))
    print("tables: ", config.rel(out_md))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--note", default="")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--agents", nargs="+", default=sorted(REGISTRY),
                        choices=sorted(REGISTRY))
    args = parser.parse_args(argv)

    if args.freeze:
        manifest = freeze.write_manifest(args.note)
        print("frozen:", config.rel(config.FREEZE_MANIFEST),
              f"({len(manifest['files'])} files, model "
              f"{manifest['model_id']})")
        return 0

    mode = args.mode.upper()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bench_id = f"bench-{args.mode}-{stamp}"
    planned = (bench_id, mode, args.agents, args.trials)

    diffs = freeze.verify()
    if diffs and mode == "LIVE":
        print("BLOCKED: freeze check failed:")
        for diff in diffs:
            print("  - " + diff)
        write_outputs(blocked_index(*planned, "freeze check failed"))
        return 2
    try:
        ctx = build_context(args.mode)
    except (NoCredentials, FileNotFoundError) as exc:
        print(str(exc))
        write_outputs(blocked_index(*planned, str(exc)))
        return 2

    needed = args.trials * calls_per_trial(args.agents)
    index = {
        "benchmark_id": bench_id, "mode": mode,
        "started_utc": artifacts.utc_now(),
        "model_id": ctx.model_cfg["model_id"],
        "freeze_ok": not diffs,
        "freeze_manifest_sha256": ctx.freeze_sha256,
        "planned_inference_requests": needed,
        "runs": [],
    }
    if mode == "LIVE":
        info = ctx.client.model_info()
        index["model_preflight"] = info
        remaining = ctx.client.budget.remaining()
        index["budget_remaining_before"] = remaining
        reason = None
        if not info.get("ok"):
            reason = ("model access check failed for "
                      f"{ctx.model_cfg['model_id']}: "
                      f"{info.get('error', 'generateContent unsupported')}")
        elif needed > remaining:
            reason = (f"planned {needed} requests but only {remaining} "
                      "remain in the global budget")
        if reason:
            print("BLOCKED: " + reason)
            blocked = blocked_index(*planned, reason)
            blocked["model_preflight"] = info
            write_outputs(blocked)
            return 2
        print(f"live benchmark: {needed} requests planned, "
              f"{remaining} remaining in budget")

    skipped = {}
    for trial in range(1, args.trials + 1):
        for agent_id in args.agents:
            if agent_id in skipped:
                index["runs"].append({
                    "agent": agent_id, "trial": trial, "mode": mode,
                    "status": "NOT_RUN",
                    "failure_reason": "SKIPPED: " + skipped[agent_id],
                })
                print(f"  {agent_id} trial {trial}: NOT_RUN (skipped)")
                continue
            result = load_agent(agent_id).run(ctx, trial)
            index["runs"].append({
                "agent": agent_id, "trial": trial, "mode": mode,
                "run_id": result["run_id"], "status": result["status"],
                "result": result["artifacts"]["result"],
            })
            print(f"  {agent_id} trial {trial}: {result['status']}"
                  + (f" ({result['failure_reason']})"
                     if result["failure_reason"] else ""))
            systemic = [s["status"] for s in result["stages"]
                        if s["status"] in SYSTEMIC]
            if systemic:
                # A configuration-level error would repeat identically;
                # the failed trial is kept and the rest are not sent.
                skipped[agent_id] = (
                    f"trial {trial} failed with {systemic[0]}, a "
                    "configuration-level error that a repeat cannot fix"
                )
    index["finished_utc"] = artifacts.utc_now()
    if mode == "LIVE":
        index["budget_remaining_after"] = ctx.client.budget.remaining()
    write_outputs(index)
    return 0


if __name__ == "__main__":
    sys.exit(main())
