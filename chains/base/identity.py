"""Base creation provenance. Factory originators remain unresolved without traces."""

import re

import requests
from web3 import Web3


def resolve_identity(web3, address, network="base"):
    unknown = {"status": "UNKNOWN", "deployer": None, "history_status": "NOT_CHECKED"}
    try:
        expected_chain = {"base": 8453, "base_sepolia": 84532}[network]
        if web3.eth.chain_id != expected_chain:
            return {**unknown, "reason": "RPC_CHAIN_MISMATCH"}
        token = Web3.to_checksum_address(address)
        if not web3.eth.get_code(token):
            return {**unknown, "reason": "NOT_A_CONTRACT"}
        host = "base.blockscout.com" if network == "base" else "base-sepolia.blockscout.com"
        response = requests.get(f"https://{host}/api/v2/addresses/{token}", timeout=12)
        response.raise_for_status()
        record = response.json()
        if str(record.get("hash", "")).lower() != token.lower() or record.get("is_contract") is not True:
            return {**unknown, "reason": "INVALID_EXPLORER_RECORD"}
        tx_hash = record.get("creation_transaction_hash") or ""
        creator = record.get("creator_address_hash") or ""
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash) or not Web3.is_address(creator):
            return {**unknown, "reason": "CREATION_RECORD_MISSING"}
        receipt = web3.eth.get_transaction_receipt(tx_hash)
        tx = web3.eth.get_transaction(tx_hash)
        if (receipt.get("status") != 1 or receipt.get("blockNumber") is None
                or tx.get("blockHash") != receipt.get("blockHash")
                or Web3.to_hex(receipt.get("transactionHash")).lower() != tx_hash.lower()
                or Web3.to_hex(tx.get("hash")).lower() != tx_hash.lower()):
            return {**unknown, "reason": "CREATION_RECEIPT_INVALID"}
        evidence = {"creation_tx_hash": tx_hash, "evidence_url": f"https://{host}/tx/{tx_hash}",
                    "source": "blockscout_and_rpc", "block_number": receipt["blockNumber"]}
        created = receipt.get("contractAddress")
        if tx.get("to") or not created:
            return {**unknown, **evidence, "reason": "FACTORY_TRACE_REQUIRED",
                    "reported_creator": creator, "transaction_sender": tx.get("from")}
        if (str(created).lower() != token.lower()
                or str(tx.get("from", "")).lower() != creator.lower()
                or str(receipt.get("from", "")).lower() != creator.lower()):
            return {**unknown, **evidence, "reason": "CREATION_IDENTITY_MISMATCH"}
        return {**unknown, **evidence, "status": "VERIFIED_DIRECT_CREATION",
                "deployer": Web3.to_checksum_address(creator), "reason": None}
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
        return {**unknown, "reason": "IDENTITY_PROVIDER_UNAVAILABLE"}
    except Exception:
        # RPC providers raise different exception types; an outage cannot verify identity.
        return {**unknown, "reason": "IDENTITY_RPC_UNAVAILABLE"}
