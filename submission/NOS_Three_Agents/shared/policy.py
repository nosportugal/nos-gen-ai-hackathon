"""Load the frozen masking policy and render the text all agents share."""
from __future__ import annotations

import re

from . import config
from .textmodel import SourceDoc

DECISIONS = ("MASK", "AMBIGUOUS", "KEEP")


class Policy:
    def __init__(self, data: dict, sha256: str):
        self.data = data
        self.sha256 = sha256
        self.version = data["version"]
        self.open_p = data["word_rule"]["open_punctuation"]
        self.close_p = data["word_rule"]["close_punctuation"]
        self.render_ambiguous_as = data["ambiguity_rule"][
            "render_ambiguous_as"
        ]
        self.anchor_lines = list(data["verified_anchor_lines"])
        self.categories = {
            decision: [c["id"] for c in data["categories"][decision]]
            for decision in DECISIONS
        }

    def category_ids(self, decisions=DECISIONS) -> list:
        return [c for d in decisions for c in self.categories[d]]

    def decision_of(self, category: str):
        for decision in DECISIONS:
            if category in self.categories[decision]:
                return decision
        return None

    def make_doc(self, text: str) -> SourceDoc:
        return SourceDoc(text, self.open_p, self.close_p)

    def word_rule_text(self) -> str:
        return self.data["word_rule"]["agent_text"]

    def prompt_block(self) -> str:
        """Semantic policy text, identical for every agent."""
        cats = self.data["categories"]
        rows = [
            f"MASKING POLICY (version {self.version}, provisional)",
            "",
            "MASK - every word of a value in these categories is masked:",
        ]
        rows += [f"- {c['id']}: {c['description']}" for c in cats["MASK"]]
        rows += [
            "",
            "AMBIGUOUS - values in these categories are NOT masked under "
            "this policy version:",
        ]
        rows += [
            f"- {c['id']}: {c['description']}" for c in cats["AMBIGUOUS"]
        ]
        rows += ["", "KEEP - never masked:"]
        rows += [f"- {c['id']}: {c['description']}" for c in cats["KEEP"]]
        rows += [
            "",
            "Do not mask a number, date or place merely because of its "
            "format. Mask it only when it falls in a MASK category.",
        ]
        return "\n".join(rows)


def load_policy(path=None) -> Policy:
    path = path or config.POLICY_PATH
    return Policy(config.load_json(path), config.sha256_file(path))


_PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def fill(template: str, **values: str) -> str:
    """Replace {{NAME}} placeholders in one pass over the template.

    Inserted values are never rescanned, so document text that happens to
    contain braces cannot trigger or break a substitution.
    """

    def repl(match):
        name = match.group(1)
        if name not in values:
            raise KeyError(f"unfilled placeholder {{{{{name}}}}}")
        return values[name]

    return _PLACEHOLDER.sub(repl, template)
