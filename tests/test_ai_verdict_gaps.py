"""The AI sentence must not call a token clean when the verdict was withheld -- Base.

Same defect and fix as BNB Chain: the model's context carried rug and
speculation LOW and nothing about the unfinished contract check, so Base USDC
and AERO, both INSUFFICIENT_DATA, would most likely have been summarised as low
risk once a DeepSeek key was set.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "chains" / "base"))

TOKEN = "0x940181a94A35A4569E4529A3CDfB74e38FD98631"


@pytest.fixture()
def server(monkeypatch):
    monkeypatch.setenv("RUGBUSTER_API_KEY", "")
    import api.server as srv
    importlib.reload(srv)
    monkeypatch.setattr(srv, "DEEPSEEK_API_KEY", "test-key")
    return srv


def _report(gaps: list[str]) -> dict:
    return {"address": TOKEN, "token_name": "Aerodrome", "symbol": "AERO",
            "rug_status": "LOW", "rug_score": 12, "speculation_status": "LOW",
            "speculation_score": 10, "blocking_data_gaps": gaps}


def _deepseek(server, text: str):
    response = mock.Mock()
    response.json.return_value = {"choices": [{"message": {"content": text}}]}
    response.raise_for_status.return_value = None
    return mock.patch.object(server.requests, "post", return_value=response)


def test_the_model_is_told_what_was_not_established(server):
    context = server.build_ai_scan_context(_report(["contract_capability"]))
    assert context["checks_that_could_not_run"] == ["what a matched contract function can do"]


def test_the_prompt_forbids_calling_a_withheld_token_safe(server):
    with _deepseek(server, "Not enough data to judge.") as post:
        server.fetch_deepseek_verdict(_report(["contract_capability"]))
    prompt = post.call_args.kwargs["json"]["messages"][1]["content"]
    assert "NOT describe the token as safe" in prompt


def test_a_reassuring_answer_on_a_withheld_verdict_is_replaced(server):
    with _deepseek(server, "Healthy liquidity, low risk, looks safe."):
        verdict = server.fetch_deepseek_verdict(_report(["contract_capability"]))
    assert verdict.startswith("Not enough data to judge this token.")


def test_a_finished_check_keeps_the_model_sentence(server):
    text = "Deep liquidity and low risk."
    with _deepseek(server, text):
        assert server.fetch_deepseek_verdict(_report([])) == text
