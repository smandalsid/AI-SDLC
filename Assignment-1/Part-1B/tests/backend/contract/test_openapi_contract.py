"""The generated OpenAPI matches the committed contract (Principle IX)."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from app.api.main import create_app
from app.llm.stub_client import StubLLMClient
from app.settings import Settings

pytestmark = pytest.mark.covers("FR-8", "FR-14", "GR-5", "INV-1", "INV-8")

CONTRACT = (
    Path(__file__).resolve().parents[3] / "specs/001-nl-reminder-agent/contracts/openapi.yaml"
)
METHODS = {"get", "post", "put", "patch", "delete"}


def _contract() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return loaded


def _generated() -> dict[str, Any]:
    app = create_app(settings=Settings(_env_file=None), llm_client=StubLLMClient())
    document: dict[str, Any] = app.openapi()
    return document


def _resolve(node: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in node:
        target: Any = doc
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    if "anyOf" in node:
        branches = [b for b in node["anyOf"] if b.get("type") != "null"]
        if len(branches) == 1:
            return _resolve(branches[0], doc)
    return node


def _shape(node: dict[str, Any], doc: dict[str, Any]) -> object:
    """Property names and required lists of an object schema, recursively."""
    node = _resolve(node, doc)
    if "properties" in node:
        return {
            "required": sorted(node.get("required", [])),
            "properties": {k: _shape(v, doc) for k, v in sorted(node["properties"].items())},
        }
    if node.get("type") == "array":
        return {"items": _shape(node["items"], doc)}
    return "leaf"


def _operations(doc: dict[str, Any]) -> dict[tuple[str, str], set[str]]:
    return {
        (path, method): set(operation["responses"])
        for path, item in doc["paths"].items()
        for method, operation in item.items()
        if method in METHODS
    }


def _json_schema(response: dict[str, Any]) -> dict[str, Any]:
    schema: dict[str, Any] = response["content"]["application/json"]["schema"]
    return schema


def _schema_named(doc: dict[str, Any], name: str) -> object:
    return _shape({"$ref": f"#/components/schemas/{name}"}, doc)


def test_paths_methods_and_status_codes_match_the_contract() -> None:
    assert _operations(_generated()) == _operations(_contract())


@pytest.mark.parametrize("name", ["InterpretRequest", "InterpretResponse", "ProposedAction"])
def test_the_named_schemas_have_the_contract_property_names_and_required_lists(
    name: str,
) -> None:
    generated = _generated()
    # Compared by shape: nested schema names (Reminder, ReminderIn) may differ.
    assert _schema_named(generated, name) == _schema_named(_contract(), name)


def test_every_error_status_uses_the_contract_error_body() -> None:
    contract, generated = _contract(), _generated()
    wanted = _schema_named(contract, "ErrorBody")
    operation = generated["paths"]["/api/v1/actions"]["post"]["responses"]
    for status in ("413", "422", "500", "502", "503", "504"):
        assert _shape(_json_schema(operation[status]), generated) == wanted, status


def test_the_success_response_is_the_interpret_response() -> None:
    contract, generated = _contract(), _generated()
    operation = generated["paths"]["/api/v1/actions"]["post"]["responses"]["200"]
    assert _shape(_json_schema(operation), generated) == _schema_named(
        contract, "InterpretResponse"
    )
