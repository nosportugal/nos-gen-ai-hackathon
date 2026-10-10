from submission.anonymizer.agents.detector import format_category
from submission.anonymizer.base_prompt import compose
from submission.anonymizer.categories import Category
from submission.anonymizer.llm import LLMClient
from submission.anonymizer.schemas import ContextResult, Finding


def check_context(text: str, category: Category, findings: list[Finding],
                  base: str, client: LLMClient) -> ContextResult:
    findings_block = "\n".join(
        f'- "{f.text}" (linha: "{f.context}")' for f in findings
    )
    prompt = compose(base, "context_checker", text,
                     category_block=format_category(category),
                     findings_block=findings_block)
    result = client.generate_json(prompt, ContextResult)

    additions = [
        addition.model_copy(update={"category": category.id})
        for addition in result.additions
    ]
    return ContextResult(additions=additions, rejections=result.rejections)
