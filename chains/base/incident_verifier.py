"""Verify curated V2 liquidity-removal evidence using independent RPC data."""

from web3 import Web3

from .identity import resolve_identity

WETH = "0x4200000000000000000000000000000000000006"
PAIR_ABI = [{"type": "function", "name": name, "inputs": [],
             "outputs": [{"type": "address"}], "stateMutability": "view"}
            for name in ("token0", "token1", "factory")]


def verify_incident(web3, candidate):
    if web3.eth.chain_id != 8453:
        raise ValueError("Wrong RPC chain")
    if candidate.get("review_status") != "REVIEWED" or not candidate.get("report_url", "").startswith("https://"):
        raise ValueError("Curator review and an independent report are required")
    token = Web3.to_checksum_address(candidate["token"])
    actor = Web3.to_checksum_address(candidate["deployer"])
    identity = resolve_identity(web3, token)
    if identity.get("status") != "VERIFIED_DIRECT_CREATION" or identity.get("deployer", "").lower() != actor.lower():
        raise ValueError("Incident actor does not match verified token creation")
    tx_hash = candidate["transaction_hash"]
    receipt = web3.eth.get_transaction_receipt(tx_hash)
    tx = web3.eth.get_transaction(tx_hash)
    block = web3.eth.get_block(receipt["blockNumber"])
    if (receipt["status"] != 1 or str(tx["from"]).lower() != actor.lower()
            or str(receipt["from"]).lower() != actor.lower()
            or Web3.to_hex(tx["hash"]).lower() != tx_hash.lower()
            or Web3.to_hex(receipt["transactionHash"]).lower() != tx_hash.lower()
            or receipt["blockHash"] != block["hash"] or tx["blockHash"] != block["hash"]
            or web3.eth.block_number - receipt["blockNumber"] < 64
            or identity["block_number"] > receipt["blockNumber"]):
        raise ValueError("Unconfirmed or mismatched incident transaction")
    pool = Web3.to_checksum_address(candidate["pool"])
    pair = web3.eth.contract(address=pool, abi=PAIR_ABI)
    assets = [pair.functions.token0().call(), pair.functions.token1().call()]
    if {a.lower() for a in assets} != {token.lower(), WETH.lower()}:
        raise ValueError("Pool assets do not match incident")
    factory = Web3.to_checksum_address(candidate["factory"])
    if pair.functions.factory().call().lower() != factory.lower():
        raise ValueError("Pool factory mismatch")
    abi = [{"type": "function", "name": "getPair", "inputs": [{"type": "address"}, {"type": "address"}],
            "outputs": [{"type": "address"}], "stateMutability": "view"}]
    registered = web3.eth.contract(address=factory, abi=abi).functions.getPair(*assets).call()
    if registered.lower() != pool.lower():
        raise ValueError("Factory did not register this pool")
    burn_topic = Web3.keccak(text="Burn(address,uint256,uint256,address)")
    # LeetSwap's verified pair ABI uses uint256 reserves, not Uniswap V2 uint112.
    sync_topic = Web3.keccak(text="Sync(uint256,uint256)")
    logs = [l for l in receipt["logs"] if l["address"].lower() == pool.lower()]
    burns = [l for l in logs if l["topics"] and l["topics"][0] == burn_topic]
    if len(burns) != 1:
        raise ValueError("Expected exactly one unambiguous pool Burn")
    burn = burns[0]
    syncs = [l for l in logs if l["topics"] and l["topics"][0] == sync_topic and l["logIndex"] < burn["logIndex"]]
    if not syncs:
        raise ValueError("Missing post-removal reserves")
    amounts = web3.codec.decode(["uint256", "uint256"], burn["data"])
    reserves = web3.codec.decode(["uint256", "uint256"], syncs[-1]["data"])
    quote = next(i for i, a in enumerate(assets) if a.lower() == WETH.lower())
    removed = amounts[quote]
    if removed <= 0:
        raise ValueError("No WETH removal")
    fraction_bps = removed * 10000 // (removed + reserves[quote])
    if fraction_bps < 9000:
        raise ValueError("Does not meet the reviewed >=90% WETH removal evidence threshold")
    return {"verification": "RPC_VERIFIED_CURATED_INCIDENT", "chain_id": 8453,
            "token": token.lower(), "deployer": actor.lower(), "transaction_hash": tx_hash.lower(),
            "pool": pool.lower(), "factory": factory.lower(), "block_number": receipt["blockNumber"],
            "block_hash": Web3.to_hex(block["hash"]), "timestamp": block["timestamp"],
            "creation_tx_hash": identity["creation_tx_hash"], "burn_log_index": burn["logIndex"],
            "weth_removed_wei": str(removed), "weth_remaining_wei": str(reserves[quote]),
            "weth_removed_bps": fraction_bps, "report_url": candidate["report_url"],
            "review_status": "REVIEWED", "incident_type": "REPORTED_RUG_WITH_VERIFIED_LIQUIDITY_REMOVAL",
            "evidence_url": f"https://base.blockscout.com/tx/{tx_hash}",
            "limitations": "Curated report establishes incident classification; liquidity removal alone does not prove fraud."}
