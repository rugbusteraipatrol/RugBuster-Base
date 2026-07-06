"""Shared network helpers for RugBuster Base scripts."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

NETWORKS = {
    "base": {
        "rpc_env": "BASE_RPC_URL",
        "default_rpc": "https://mainnet.base.org",
        "chain_id": 8453,
        "label": "Base Mainnet",
    },
    "base_sepolia": {
        "rpc_env": "BASE_SEPOLIA_RPC_URL",
        "default_rpc": "https://sepolia.base.org",
        "chain_id": 84532,
        "label": "Base Sepolia",
    },
}


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def resolve_network() -> str:
    raw = (os.getenv("RUGBUSTER_NETWORK") or "base").strip().lower()
    if raw == "mainnet":
        raw = "base"
    if raw not in NETWORKS:
        raise RuntimeError(f"Unsupported RUGBUSTER_NETWORK: {raw}")
    return raw


def resolve_rpc(network: str) -> str:
    config = NETWORKS[network]
    return os.getenv(config["rpc_env"]) or config["default_rpc"]

