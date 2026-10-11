"""Run one anonymization agent once.

Usage (workspace root, inside the virtual environment):

    python -I run_agent.py --agent A --mode mock
    python -I run_agent.py --agent B --mode mock --trial 2
    python -I run_agent.py --agent C --mode live      # uses the API key

Mock mode needs no credentials and no network. Its outputs come from a
local stand-in and are labelled MOCK; they are not Gemini results.

Live mode counts against the global request budget (A: 1 request,
B: 2, C: 1, plus at most one transient retry per stage) and is refused
unless the freeze manifest matches the current files.

Exit code: 0 valid candidate, 1 invalid candidate or pipeline failure,
2 blocked before running.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents import REGISTRY, load_agent  # noqa: E402
from shared import freeze  # noqa: E402
from shared.runner import VALID, NoCredentials, build_context  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--agent", required=True, choices=sorted(REGISTRY))
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--trial", type=int, default=1)
    args = parser.parse_args(argv)

    if args.mode == "live":
        diffs = freeze.verify()
        if diffs:
            print("BLOCKED: freeze check failed:")
            for diff in diffs:
                print("  - " + diff)
            return 2
    try:
        ctx = build_context(args.mode)
    except (NoCredentials, FileNotFoundError) as exc:
        print(str(exc))
        return 2
    result = load_agent(args.agent).run(ctx, args.trial)
    view = {
        key: result[key]
        for key in ("agent_id", "run_id", "mode", "label", "status",
                    "failure_reason", "hashes", "validation", "usage",
                    "timings", "artifacts")
    }
    print(json.dumps(view, ensure_ascii=False, indent=2))
    return 0 if result["status"] == VALID else 1


if __name__ == "__main__":
    sys.exit(main())
