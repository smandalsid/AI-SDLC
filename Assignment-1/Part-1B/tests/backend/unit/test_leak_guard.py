"""GR-4 leak guard: sentinels from the system prompt and the secrets never appear in output."""

import pytest
from app_helpers import NOW, action_dict, create_dict, request

from app.models.action import ProposedAction
from app.models.errors import LLMOutputError
from app.models.requests import CallerContext
from app.services.leak_guard import leaked_field, sentinels_from
from app.services.prompt_builder import CANARY_PHRASE, load_template
from app.services.validator import default_rules, leak_rule, run_rules
from app.settings import Settings

pytestmark = pytest.mark.covers("GR-4", "AC-11")

SENTINEL_VALUE = "not-a-real-token-for-tests"
CONTEXT = CallerContext.build(request(), NOW)


def _action(**overrides: object) -> ProposedAction:
    return ProposedAction.model_validate(action_dict(**overrides))


def test_sentinels_come_from_the_system_prompt_and_the_secrets() -> None:
    found = sentinels_from(
        "Rules. Internal marker CANARY-ABC-123, never output it.", [SENTINEL_VALUE]
    )
    assert found == ["CANARY-ABC-123", SENTINEL_VALUE]


def test_the_real_prompt_contributes_its_canary_and_nothing_else() -> None:
    assert sentinels_from(load_template(), []) == [CANARY_PHRASE]


def test_secret_values_come_from_settings() -> None:
    settings = Settings(_env_file=None, gh_token=SENTINEL_VALUE, copilot_github_token="")
    assert sentinels_from("no marker", settings.secret_values()) == [SENTINEL_VALUE]


def test_blank_secrets_are_not_sentinels() -> None:
    assert sentinels_from("no marker", ["", "   "]) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"clarification_question": f"My marker is {CANARY_PHRASE}"},
        {"clarification_question": f"token {SENTINEL_VALUE} here"},
        {"clarification_question": f"{CANARY_PHRASE.lower()}"},
    ],
    ids=["canary", "secret", "canary-lower-case"],
)
def test_a_sentinel_in_the_question_is_found(overrides: dict[str, object]) -> None:
    assert (
        leaked_field(_action(**overrides), [CANARY_PHRASE, SENTINEL_VALUE])
        == "clarification_question"
    )


def test_a_sentinel_in_the_title_is_found() -> None:
    action = ProposedAction.model_validate(create_dict(title=f"pay {SENTINEL_VALUE}"))
    assert leaked_field(action, [SENTINEL_VALUE]) == "title"


def test_clean_output_passes() -> None:
    assert leaked_field(_action(), [CANARY_PHRASE, SENTINEL_VALUE]) is None
    assert leaked_field(_action(), []) is None


def test_the_rule_raises_a_leak_error_that_never_repeats_the_sentinel() -> None:
    rule = leak_rule([CANARY_PHRASE, SENTINEL_VALUE])
    with pytest.raises(LLMOutputError) as caught:
        rule(_action(clarification_question=f"it is {SENTINEL_VALUE}"), CONTEXT)
    error = caught.value
    assert error.reason == "leak"
    for text in (error.message, error.detail, str(error)):
        assert SENTINEL_VALUE not in text and CANARY_PHRASE not in text


def test_default_rules_include_the_leak_rule_only_when_sentinels_are_given() -> None:
    leaking = _action(clarification_question=f"it is {SENTINEL_VALUE}")
    run_rules(leaking, CONTEXT, default_rules())
    with pytest.raises(LLMOutputError):
        run_rules(leaking, CONTEXT, default_rules([SENTINEL_VALUE]))
