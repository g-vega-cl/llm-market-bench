"""TDD suite for verifying complete removal of Contrarian Agent components."""


def test_config_has_no_contrarian_agent_id():

    import core.config as config

    assert not hasattr(config, "CONTRARIAN_AGENT_ID")


def test_models_has_no_contrarian_agent_response():

    import core.models as models

    assert not hasattr(models, "ContrarianAgentResponse")


def test_prompt_factory_has_no_contrarian_messages():

    from core.llm.prompt_factory import PromptFactory

    assert not hasattr(PromptFactory, "build_contrarian_messages")


def test_verifier_prompt_has_no_contrarian_context():

    from core.llm.prompts import VERIFIER_USER_PROMPT_TEMPLATE

    assert "Contrarian Insights" not in VERIFIER_USER_PROMPT_TEMPLATE
    assert "{contrarian_context}" not in VERIFIER_USER_PROMPT_TEMPLATE


def test_verifier_messages_no_contrarian_param():

    import inspect

    from core.llm.prompt_factory import PromptFactory

    sig = inspect.signature(PromptFactory.build_verifier_messages)
    assert "contrarian_context" not in sig.parameters


def test_verify_trading_decision_no_contrarian_param():

    import inspect

    from core.llm.verification import verify_trading_decision

    sig = inspect.signature(verify_trading_decision)
    assert "contrarian_context" not in sig.parameters


def test_main_has_no_run_contrarian_analysis():

    import main

    assert not hasattr(main, "run_contrarian_analysis")
