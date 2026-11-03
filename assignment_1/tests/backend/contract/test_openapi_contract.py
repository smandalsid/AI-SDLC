from pathlib import Path
from typing import Any

import pytest
import yaml
from app.api.error_handlers import CODE_BY_HTTP_STATUS, STATUS_BY_CODE
from app.main import create_app
from fastapi.testclient import TestClient

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "002-user-authentication"
    / "contracts"
    / "openapi.yaml"
)
SERVER_PREFIX = "/api/v1"
METHODS = {"get", "post", "put", "patch", "delete"}

# Differences between the 002 contract and the app that a later story still delivers. Each story
# checkpoint deletes its entries; test_no_pending_contract_items (T124) requires all to be empty.
PENDING_OPERATIONS_NOT_IN_APP = {
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("POST", "/auth/logout"),
}
PENDING_OPERATIONS_ONLY_IN_APP = {("GET", "/users")}
PENDING_STATUSES_NOT_IN_APP = {"401"}
PENDING_ERROR_CODES_ONLY_IN_APP = {"user_not_found"}
PENDING_BODY_FIELDS_ONLY_IN_APP = {"user_id"}

# Parsed JSON and YAML documents have no fixed shape.
Document = dict[str, Any]
Operation = tuple[str, str]


# Returns whatever node the reference points at.
def follow(document: Document, ref: str) -> Any:
    node: Any = document  # walks the same untyped document
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node


def resolve(document: Document, node: Document) -> Document:
    while "$ref" in node:
        node = follow(document, node["$ref"])
    return node


def shape(document: Document, schema: Document) -> Document:
    """Property names, required lists, and array items; the names of schemas are irrelevant."""
    schema = resolve(document, schema)
    result: Document = {}
    if "properties" in schema:
        result["properties"] = {
            name: shape(document, sub) for name, sub in schema["properties"].items()
        }
    if "required" in schema:
        result["required"] = sorted(schema["required"])
    if "items" in schema:
        result["items"] = shape(document, schema["items"])
    return result


def body_shape(document: Document, container: Document) -> Document | None:
    content = resolve(document, container).get("content", {})
    schema = content.get("application/json", {}).get("schema")
    return None if schema is None else shape(document, schema)


def without_fields(node: Document, names: set[str]) -> Document:
    """Drops pending field names from a request body shape (properties and required lists)."""
    result: Document = {}
    if "properties" in node:
        result["properties"] = {
            name: without_fields(sub, names)
            for name, sub in node["properties"].items()
            if name not in names
        }
    if "required" in node:
        result["required"] = [name for name in node["required"] if name not in names]
    if "items" in node:
        result["items"] = without_fields(node["items"], names)
    return result


def operations(document: Document, prefix: str) -> dict[Operation, Document]:
    found: dict[Operation, Document] = {}
    for path, item in document["paths"].items():
        for method, operation in item.items():
            if method in METHODS:
                found[(method.upper(), path.removeprefix(prefix))] = operation
    return found


def parameter_set(document: Document, operation: Document) -> set[tuple[str, str, bool]]:
    resolved = (resolve(document, p) for p in operation.get("parameters", []))
    return {(p["name"], p["in"], p.get("required", False)) for p in resolved}


def response_shapes(document: Document, operation: Document) -> dict[str, Document | None]:
    return {
        status: body_shape(document, response)
        for status, response in operation["responses"].items()
    }


CONTRACT: Document = yaml.safe_load(CONTRACT_PATH.read_text())
APP: Document = create_app(wait_for_db=lambda: None).openapi()
CONTRACT_OPERATIONS = operations(CONTRACT, "")
APP_OPERATIONS = operations(APP, SERVER_PREFIX)
OPERATION_IDS = [f"{method} {path}" for method, path in CONTRACT_OPERATIONS]


def test_contract_paths_and_methods_are_exactly_the_apps() -> None:
    assert set(APP_OPERATIONS) - PENDING_OPERATIONS_ONLY_IN_APP == (
        set(CONTRACT_OPERATIONS) - PENDING_OPERATIONS_NOT_IN_APP
    )


COMPARED_OPERATIONS = [
    key for key in CONTRACT_OPERATIONS if key not in PENDING_OPERATIONS_NOT_IN_APP
]


@pytest.fixture(
    params=COMPARED_OPERATIONS,
    ids=[f"{method} {path}" for method, path in COMPARED_OPERATIONS],
)
def pair(request: pytest.FixtureRequest) -> tuple[Document, Document]:
    key: Operation = request.param
    assert key in APP_OPERATIONS, f"{key} is missing from the app"
    return CONTRACT_OPERATIONS[key], APP_OPERATIONS[key]


def test_status_codes_match(pair: tuple[Document, Document]) -> None:
    contract, app = pair

    assert set(app["responses"]) == set(contract["responses"]) - PENDING_STATUSES_NOT_IN_APP


def test_response_schemas_match_by_property_names_and_required_lists(
    pair: tuple[Document, Document],
) -> None:
    contract, app = pair

    expected = response_shapes(CONTRACT, contract)
    for status in PENDING_STATUSES_NOT_IN_APP:
        expected.pop(status, None)
    assert response_shapes(APP, app) == expected


def test_request_body_schemas_match(pair: tuple[Document, Document]) -> None:
    contract, app = pair

    app_body = app.get("requestBody")
    contract_body = contract.get("requestBody")
    assert (app_body is None) == (contract_body is None)
    if app_body is not None and contract_body is not None:
        app_shape = body_shape(APP, app_body)
        contract_shape = body_shape(CONTRACT, contract_body)
        assert app_shape is not None and contract_shape is not None
        assert without_fields(app_shape, PENDING_BODY_FIELDS_ONLY_IN_APP) == contract_shape
        assert app_body.get("required", False) == contract_body.get("required", False)


def test_parameters_match_by_name_location_and_required(pair: tuple[Document, Document]) -> None:
    contract, app = pair

    assert parameter_set(APP, app) == parameter_set(CONTRACT, contract)


def contract_error_codes() -> set[str]:
    code = CONTRACT["components"]["schemas"]["ErrorResponse"]["properties"]["error"]["properties"][
        "code"
    ]
    return set(code["enum"])


def test_the_contract_lists_exactly_the_error_codes_the_app_defines() -> None:
    defined = (
        set(STATUS_BY_CODE)
        | set(CODE_BY_HTTP_STATUS.values())
        | {"validation_error", "service_unavailable", "internal_error"}
    )

    assert contract_error_codes() == defined - PENDING_ERROR_CODES_ONLY_IN_APP


def test_unknown_routes_and_wrong_methods_return_codes_from_the_contract() -> None:
    client = TestClient(create_app(wait_for_db=lambda: None))

    returned = {
        client.get("/nowhere").json()["error"]["code"],
        client.delete("/api/v1/buses").json()["error"]["code"],
    }

    assert returned <= contract_error_codes()
