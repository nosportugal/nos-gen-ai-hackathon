from submission.anonymizer.base_prompt import compose
from submission.anonymizer.categories import Category
from submission.anonymizer.llm import LLMClient
from submission.anonymizer.schemas import DetectorResult, Finding


def format_category(category: Category) -> str:
    examples = "; ".join(category.examples)
    do_not_mask = "; ".join(category.do_not_mask)
    return (
        f"Categoria: {category.id} ({category.name})\n"
        f"Descrição: {category.description}\n"
        f"Exemplos: {examples}\n"
        f"Não anonimizar: {do_not_mask}"
    )


def detect(text: str, category: Category, base: str,
           client: LLMClient) -> list[Finding]:
    prompt = compose(base, "detector", text,
                     category_block=format_category(category))
    result = client.generate_json(prompt, DetectorResult)

    # The detector only knows its own category, so its id is
    # authoritative over whatever label the model wrote.
    return [
        finding.model_copy(update={"category": category.id})
        for finding in result.findings
    ]
