from types import SimpleNamespace

import pytest

from api import server
from chains.base import identity

TOKEN = "0x" + "1" * 40
CREATOR = "0x" + "2" * 40
TX = "0x" + "3" * 64
BLOCK = bytes.fromhex("4" * 64)


@pytest.fixture
def provider(monkeypatch):
    receipt = {"status": 1, "blockNumber": 123, "blockHash": BLOCK,
               "contractAddress": TOKEN, "from": CREATOR,
               "transactionHash": bytes.fromhex(TX[2:])}
    tx = {"hash": bytes.fromhex(TX[2:]), "from": CREATOR, "to": None, "blockHash": BLOCK}
    record = {"hash": TOKEN, "is_contract": True, "creator_address_hash": CREATOR,
              "creation_transaction_hash": TX}
    eth = SimpleNamespace(chain_id=8453, get_code=lambda _: b"code",
                          get_transaction_receipt=lambda _: receipt,
                          get_transaction=lambda _: tx)
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: record)
    monkeypatch.setattr(identity.requests, "get", lambda *a, **kw: response)
    return SimpleNamespace(eth=eth), receipt, tx, record


def test_direct_creation_verified(provider):
    result = identity.resolve_identity(provider[0], TOKEN)
    assert result["status"] == "VERIFIED_DIRECT_CREATION"
    assert result["deployer"] == CREATOR
    assert result["history_status"] == "NOT_CHECKED"


@pytest.mark.parametrize("case", ["factory", "creator", "token", "failed", "chain", "no_code", "hash", "block"])
def test_bad_or_incomplete_provenance_never_verified(provider, case):
    web3, receipt, tx, record = provider
    if case == "factory":
        tx["to"] = CREATOR
        receipt["contractAddress"] = None
    elif case == "creator":
        record["creator_address_hash"] = TOKEN
    elif case == "token":
        receipt["contractAddress"] = CREATOR
    elif case == "failed":
        receipt["status"] = 0
    elif case == "chain":
        web3.eth.chain_id = 1
    elif case == "no_code":
        web3.eth.get_code = lambda _: b""
    elif case == "hash":
        tx["hash"] = b"wrong"
    elif case == "block":
        tx["blockHash"] = b"wrong"
    result = identity.resolve_identity(web3, TOKEN)
    assert result["status"] == "UNKNOWN"
    assert result["deployer"] is None


def test_provider_outage(provider, monkeypatch):
    def fail(*args, **kwargs):
        raise identity.requests.Timeout()
    monkeypatch.setattr(identity.requests, "get", fail)
    assert identity.resolve_identity(provider[0], TOKEN)["status"] == "UNKNOWN"


def test_api_metadata_never_good(monkeypatch):
    monkeypatch.setenv("RUGBUSTER_NETWORK", "base")
    metadata = {"name": "Example", "symbol": "EX", "decimals": 18, "total_supply": 1000}
    report = server.build_report_from_metadata(TOKEN, metadata, None, "test")
    result = server.compact_score_response(report, "test")
    assert result["label"] == "UNKNOWN"
    assert result["rug_score"] is None
    assert result["risk_percent"] is None
    assert result["coverage"]["deployer_history"] == "NOT_CHECKED"
    assert "incomplete" in server.verdict_text(report)


def test_old_and_wrong_network_cache_rejected(monkeypatch):
    monkeypatch.setenv("RUGBUSTER_NETWORK", "base")
    server.SCAN_CACHE.clear()
    for report in ({"risk_engine": "old"},
                   {"risk_engine": server.RISK_ENGINE_VERSION, "network": "Base Sepolia"}):
        server.put_cached_report(TOKEN, report)
        assert server.lookup_cached_score(TOKEN) is None


def test_unknown_publish_never_reaches_rpc(monkeypatch):
    monkeypatch.setattr(server, "get_web3", lambda: pytest.fail("must not touch RPC"))
    with pytest.raises(RuntimeError, match="incomplete"):
        server.publish_report_modules({"rug_score": None})


def test_noncontract_scan_rejected(provider, monkeypatch):
    provider[0].eth.get_code = lambda _: b""
    monkeypatch.setattr(server, "get_web3", lambda: provider[0])
    monkeypatch.setenv("RUGBUSTER_NETWORK", "base")
    with pytest.raises(ValueError, match="not a deployed"):
        server.scan_token(TOKEN)


def test_unverified_history_cannot_manufacture_rug_finding():
    from chains.base.risk_engine import score_token
    result = score_token({"name": "Example", "symbol": "EX", "decimals": 18,
                          "total_supply": 1000, "creator_rug_rate": 100}).rug
    assert result.status == "INSUFFICIENT_DATA"
    assert not any("rug rate" in reason for reason in result.reasons)


def test_market_outage_remains_unknown(provider, monkeypatch):
    monkeypatch.setenv("RUGBUSTER_NETWORK", "base")
    monkeypatch.setattr(server, "get_web3", lambda: provider[0])
    provider[0].eth.get_transaction_count = lambda _: 0
    monkeypatch.setattr(server, "get_onchain_metadata", lambda *a: {
        "name": "Example", "symbol": "EX", "decimals": 18, "total_supply": 1000})
    monkeypatch.setattr(server, "resolve_identity", lambda *a: {"status": "UNKNOWN"})
    def fail(*args):
        raise TimeoutError()
    monkeypatch.setattr(server, "get_market_data", fail)
    report = server.scan_token(TOKEN)
    assert report["rug_status"] == "INSUFFICIENT_DATA"
    assert report["speculation_status"] == "UNKNOWN"
    assert report["source"] == "market_provider_unavailable"


def test_api_invalid_address_returns_400():
    with server.app.test_client() as client:
        assert client.get("/score?address=invalid").status_code == 400


def test_cache_expired_rejected(monkeypatch):
    monkeypatch.setenv("RUGBUSTER_NETWORK", "base")
    server.put_cached_report(TOKEN, {"risk_engine": server.RISK_ENGINE_VERSION,
                                   "network": "Base Mainnet"})
    server.SCAN_CACHE[TOKEN]["ts"] = 0
    assert server.get_cached_report(TOKEN) is None
