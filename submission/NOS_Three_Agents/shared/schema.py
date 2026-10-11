"""A small JSON-schema-subset validator and the Gemini schema converter.

Supported keywords: type (object, array, string, integer), properties,
required, additionalProperties (false), items, enum, minimum, maxItems,
maxLength. That is all the ledger and span schemas use.
"""
from __future__ import annotations

_GEMINI_TYPES = {
    "object": "OBJECT",
    "array": "ARRAY",
    "string": "STRING",
    "integer": "INTEGER",
}


def validate(instance, schema, path="$") -> list:
    """Return a list of error strings; empty means valid."""
    errors = []
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(instance, dict):
            return [f"{path}: expected object"]
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{path}: missing property '{name}'")
        if schema.get("additionalProperties") is False:
            for name in instance:
                if name not in props:
                    errors.append(f"{path}: unexpected property '{name}'")
        for name, sub in props.items():
            if name in instance:
                errors += validate(instance[name], sub, f"{path}.{name}")
    elif kind == "array":
        if not isinstance(instance, list):
            return [f"{path}: expected array"]
        limit = schema.get("maxItems")
        if limit is not None and len(instance) > limit:
            errors.append(f"{path}: more than {limit} items")
        sub = schema.get("items")
        if sub:
            for k, item in enumerate(instance):
                errors += validate(item, sub, f"{path}[{k}]")
    elif kind == "string":
        if not isinstance(instance, str):
            return [f"{path}: expected string"]
        limit = schema.get("maxLength")
        if limit is not None and len(instance) > limit:
            errors.append(f"{path}: longer than {limit} characters")
    elif kind == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            return [f"{path}: expected integer"]
        low = schema.get("minimum")
        if low is not None and instance < low:
            errors.append(f"{path}: below minimum {low}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value not in enum")
    return errors


def to_gemini_schema(schema: dict) -> dict:
    """Convert to the Gemini ``responseSchema`` dialect.

    Keywords the API does not accept (additionalProperties, maxLength,
    minimum) are dropped; they remain enforced by ``validate`` locally.
    """
    out = {"type": _GEMINI_TYPES[schema["type"]]}
    if "description" in schema:
        out["description"] = schema["description"]
    if "enum" in schema:
        out["enum"] = list(schema["enum"])
    if "maxItems" in schema:
        out["maxItems"] = schema["maxItems"]
    if "properties" in schema:
        out["properties"] = {
            k: to_gemini_schema(v) for k, v in schema["properties"].items()
        }
        out["propertyOrdering"] = list(schema["properties"])
    if "required" in schema:
        out["required"] = list(schema["required"])
    if "items" in schema:
        out["items"] = to_gemini_schema(schema["items"])
    return out
