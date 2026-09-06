from types import SimpleNamespace

import pytest
from web3 import Web3

from chains.base import incident_verifier as verifier

TOKEN = "0x" + "1" * 40
ACTOR = "0x" + "2" * 40
POOL = "0x" + "3" * 40
FACTORY = "0x" + "4" * 40
HASH = "0x" + "5" * 64
BLOCK = bytes.fromhex("6" * 64)


@pytest.fixture
def evidence(monkeypatch):
    codec = Web3().codec
    logs = [
        {"address": POOL, "logIndex": 1, "topics": [Web3.keccak(text="Sync(uint256,uint256)")],
         "data": codec.encode(["uint256", "uint256"], [100, 5])},
        {"address": POOL, "logIndex": 2, "topics": [Web3.keccak(text="Burn(address,uint256,uint256,address)")],
         "data": codec.encode(["uint256", "uint256"], [100, 95])}]
    receipt = {"status": 1, "from": ACTOR, "blockNumber": 100, "blockHash": BLOCK,
               "transactionHash": bytes.fromhex(HASH[2:]), "logs": logs}
    tx = {"from": ACTOR, "hash": bytes.fromhex(HASH[2:]), "blockHash": BLOCK}
    def fn(value):
        return lambda *args: SimpleNamespace(call=lambda: value)
    functions = SimpleNamespace(token0=fn(TOKEN), token1=fn(verifier.WETH), factory=fn(FACTORY), getPair=fn(POOL))
    eth = SimpleNamespace(chain_id=8453, block_number=1000, get_transaction_receipt=lambda _: receipt,
                          get_transaction=lambda _: tx, get_block=lambda _: {"hash": BLOCK, "timestamp": 1000},
                          contract=lambda **kw: SimpleNamespace(functions=functions))
    identity = {"status": "VERIFIED_DIRECT_CREATION", "deployer": ACTOR,
                "block_number": 90, "creation_tx_hash": HASH}
    monkeypatch.setattr(verifier, "resolve_identity", lambda *a: identity)
    candidate = {"token": TOKEN, "deployer": ACTOR, "pool": POOL, "factory": FACTORY,
                 "transaction_hash": HASH, "review_status": "REVIEWED", "report_url": "https://example.org/review"}
    return SimpleNamespace(eth=eth, codec=codec), candidate, receipt, tx, identity


def test_valid_evidence(evidence):
    result = verifier.verify_incident(*evidence[:2])
    assert result["weth_removed_bps"] == 9500
    assert result["verification"] == "RPC_VERIFIED_CURATED_INCIDENT"


@pytest.mark.parametrize("case", ["chain", "actor", "review", "receipt", "reorg", "young", "creation", "burn", "sync", "pool", "ratio"])
def test_bad_evidence_rejected(evidence, case):
    w, c, receipt, tx, identity = evidence
    if case == "chain": w.eth.chain_id = 1
    elif case == "actor": tx["from"] = TOKEN
    elif case == "review": c["review_status"] = "UNREVIEWED"
    elif case == "receipt": receipt["status"] = 0
    elif case == "reorg": receipt["blockHash"] = b"bad"
    elif case == "young": w.eth.block_number = 101
    elif case == "creation": identity["deployer"] = TOKEN
    elif case == "burn": receipt["logs"].pop()
    elif case == "sync": receipt["logs"].pop(0)
    elif case == "pool": receipt["logs"][0]["address"] = TOKEN
    elif case == "ratio": receipt["logs"][0]["data"] = w.codec.encode(["uint256", "uint256"], [100, 500])
    with pytest.raises(ValueError):
        verifier.verify_incident(w, c)
