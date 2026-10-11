"""The three anonymization agents and their registry."""
from __future__ import annotations

import importlib

REGISTRY = {
    "A": "agents.A_gated_rewrite.agent",
    "B": "agents.B_decision_ledger.agent",
    "C": "agents.C_span_ledger.agent",
}


def load_agent(agent_id: str):
    """Return the agent module; each exposes ``run(ctx, trial)``."""
    return importlib.import_module(REGISTRY[agent_id.upper()])
