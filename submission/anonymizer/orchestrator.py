from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from submission.anonymizer.agents.context_checker import check_context
from submission.anonymizer.agents.detector import detect
from submission.anonymizer.agents.reviewer import review
from submission.anonymizer.categories import Category, load_categories
from submission.anonymizer.llm import LLMClient
from submission.anonymizer.masking import apply_findings
from submission.anonymizer.schemas import Finding


@dataclass
class PipelineResult:
    masked: str
    findings: list[Finding]
    rejected: list[str]
    unmatched: list[Finding]


def run_pipeline(text: str, base: str, client: LLMClient,
                 categories: list[Category] | None = None,
                 max_workers: int = 5) -> PipelineResult:
    """Detect -> context-check -> mask -> review -> mask again."""
    if categories is None:
        categories = load_categories()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        detected = list(pool.map(
            lambda category: detect(text, category, base, client),
            categories,
        ))

        flagged = [
            (category, findings)
            for category, findings in zip(categories, detected)
            if findings
        ]
        checks = list(pool.map(
            lambda pair: check_context(text, pair[0], pair[1], base, client),
            flagged,
        ))

    findings = [f for category_findings in detected for f in category_findings]
    rejected = []
    for check in checks:
        findings.extend(check.additions)
        rejected.extend(check.rejections)

    findings = _dedupe(f for f in findings if f.text not in rejected)
    first_pass = apply_findings(text, findings)

    # The reviewer reads the masked text, so its findings (and their
    # context lines) are applied to that text, not to the original.
    reviewed = _dedupe(review(first_pass.masked, base, client))
    second_pass = apply_findings(first_pass.masked, reviewed)

    return PipelineResult(
        masked=second_pass.masked,
        findings=findings + reviewed,
        rejected=rejected,
        unmatched=first_pass.unmatched + second_pass.unmatched,
    )


def _dedupe(findings) -> list[Finding]:
    unique = {}
    for finding in findings:
        unique.setdefault((finding.text, finding.context), finding)
    return list(unique.values())
