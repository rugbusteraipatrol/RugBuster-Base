"""A possible power never scores, and never lets a token be called clean -- Base.

Same rule as BNB Chain, different scorer: here the collector's label comes
from calculate_rugbuster_BASE_risk, and the API derives its label from the
rug and speculation statuses. Three inputs, as review asked: a selector alone,
a pattern proven from source, and a pattern left unresolved.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "chains" / "base"))

import base_collector_v1 as collector  # noqa: E402
import contract_functions as functions  # noqa: E402

MINT = "40c10f19"
BURN_OTHERS = "9dc29fac"
OWNER = "8da5cb5b"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def selector_only(*selectors: str) -> dict:
    return functions.read_bytecode("0x" + "".join(selectors) + "00" * 8)


def proven(*powers: str) -> dict:
    reading = selector_only(MINT)
    reading["source_status"] = "OK"
    reading["source_read_powers"] = list(powers)
    return functions.settle_capability(reading)


def unresolved() -> dict:
    reading = selector_only(BURN_OTHERS)
    reading["source_status"] = "OK"
    reading["unread_restrictions"]["burn(address,uint256)"] = "modifier onlyMinter is not defined"
    return functions.settle_capability(reading)


def _v6(backdoor: dict | None) -> dict:
    v6 = {"concentration": {"concentration_risk": "LOW", "top5_pct": 20.0},
          "velocity": {"is_fast_rug": False, "velocity_score": 0.0}}
    if backdoor is not None:
        v6["backdoor"] = backdoor
    return v6


TOKEN_INFO = {"name": "Solid", "symbol": "SOLID", "holders_count": 5_000}


def risk(backdoor: dict | None) -> tuple[int, list[str]]:
    return collector.calculate_rugbuster_BASE_risk(TOKEN_INFO, {}, {}, _v6(backdoor), {}, 5.0)


def classify(backdoor: dict | None, cia: dict | None = None) -> str:
    return collector.classify_BASE_token_v6(TOKEN_INFO, cia or {}, {}, _v6(backdoor), 5.0)[0]


# --- the collector's scorer ---------------------------------------------------

def test_a_selector_alone_adds_no_risk():
    assert risk(selector_only(MINT)) == risk(selector_only(OWNER))


def test_a_proven_power_adds_risk_and_names_its_basis():
    score, reasons = risk(proven("mint"))
    baseline, _ = risk(selector_only(OWNER))
    assert score > baseline
    assert "Mint power read from published source" in reasons


def test_an_unresolved_pattern_adds_no_risk():
    assert risk(unresolved()) == risk(selector_only(OWNER))


def test_a_selector_alone_withholds_good():
    assert classify(selector_only(MINT)) == "INSUFFICIENT_DATA"


def test_an_unresolved_pattern_withholds_good():
    assert classify(unresolved()) == "INSUFFICIENT_DATA"


def test_nothing_possible_is_good():
    assert classify(selector_only(OWNER)) == "GOOD"


def test_an_independent_finding_survives_the_gap():
    cia = {"wash": {"wash_detected": True, "linker_wallets_connected": True},
           "cluster": {"is_bot_farm": True}, "funding": {"all_fresh": True},
           "entropy": {"is_bot_pattern": True}}
    assert classify(selector_only(MINT), cia=cia) == "DANGER"


def test_booleans_from_an_old_reading_do_not_score():
    old = selector_only(OWNER)
    old.update({"has_mint_function": True, "has_blacklist": True, "is_proxy": False,
                "has_backdoor": True, "backdoor_risk_score": 40})
    assert risk(old) == risk(selector_only(OWNER))


# --- the API: what a caller sees ------------------------------------------------

@pytest.fixture()
def server(monkeypatch):
    monkeypatch.setenv("RUGBUSTER_API_KEY", "")
    import api.server as srv
    importlib.reload(srv)
    srv.SCAN_CACHE.clear()
    return srv


def _report(backdoor: dict) -> dict:
    return {"address": USDC, "rug_status": "LOW", "speculation_status": "LOW",
            "v6": {"backdoor": backdoor}}


def test_the_caller_sees_a_withheld_answer_and_why(server):
    body = server.compact_score_response(_report(selector_only(MINT)), "live_score")
    assert body["label"] == "INSUFFICIENT_DATA"
    assert body["blocking_data_gaps"] == ["contract_capability"]
    assert body["verdict_basis"] == "REFUSAL"


def test_the_caller_sees_good_when_nothing_was_left_unsettled(server):
    body = server.compact_score_response(_report(selector_only(OWNER)), "live_score")
    assert body["label"] == "GOOD"
    assert body["blocking_data_gaps"] == []


def test_an_unresolved_pattern_reaches_the_caller_as_a_gap(server):
    assert server.compact_score_response(_report(unresolved()), "live_score")["label"] == "INSUFFICIENT_DATA"


def test_a_report_with_no_contract_reading_is_not_good(server):
    body = server.compact_score_response(
        {"address": USDC, "rug_status": "LOW", "speculation_status": "LOW"}, "live_score")
    assert body["label"] == "INSUFFICIENT_DATA"
    assert body["blocking_data_gaps"] == ["contract_backdoor"]


def _chain(code: bytes | None = None, error: BaseException | None = None):
    class _Call:
        def __init__(self, value):
            self.value = value

        def call(self):
            return self.value

    class _Functions:
        name = staticmethod(lambda: _Call("USD Coin"))
        symbol = staticmethod(lambda: _Call("USDC"))
        decimals = staticmethod(lambda: _Call(6))
        totalSupply = staticmethod(lambda: _Call(10**15))

    class _Token:
        functions = _Functions

    class _Eth:
        @staticmethod
        def get_code(_address):
            if error:
                raise error
            return code

        @staticmethod
        def contract(address=None, abi=None):
            return _Token

    class _Web3:
        eth = _Eth

    return _Web3


def test_the_live_path_now_reads_the_contract(server):
    metadata = server.get_onchain_metadata(_chain(bytes.fromhex(MINT + "00" * 8)), USDC)
    report = server.build_report_from_metadata(USDC, metadata, None, "live_score")
    assert report["v6"]["backdoor"]["possible_powers"] == ["mint"]
    assert report["blocking_data_gaps"] == ["contract_capability"]


def test_an_unreadable_contract_on_the_live_path_is_a_gap(server):
    metadata = server.get_onchain_metadata(_chain(error=TimeoutError("rpc")), USDC)
    report = server.build_report_from_metadata(USDC, metadata, None, "live_score")
    assert report["blocking_data_gaps"] == ["contract_backdoor"]
