from chains.base.risk_engine import score_token


def test_missing_metadata_is_insufficient_data_not_elevated():
    result = score_token(
        {
            "name": "Unknown",
            "symbol": "Unknown",
            "decimals": None,
            "total_supply": None,
            "has_liquidity_evidence": False,
        }
    )

    assert result.rug.score is None
    assert result.rug.status == "INSUFFICIENT_DATA"


def test_aero_like_metadata_scores_low_rug_risk():
    result = score_token(
        {
            "name": "Aerodrome",
            "symbol": "AERO",
            "decimals": 18,
            "total_supply": 1_931_056_712_573_533_909_087_115_797,
            "has_liquidity_evidence": True,
            "liquidity_usd": 34_600_000,
            "fdv": 1_133_000_000,
            "volume24h": 4_900_000,
            "price_change_24h": 3.5,
            "buys24h": 1_500,
            "sells24h": 3_200,
            "is_known_base_asset": True,
        }
    )

    assert result.rug.status == "LOW"
    assert result.rug.score < 45
    assert result.speculation.status == "LOW"


def test_known_base_asset_skips_fdv_liquidity_ratio_penalty():
    result = score_token(
        {
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
            "total_supply": 4_301_151_702_000_000,
            "has_liquidity_evidence": True,
            "liquidity_usd": 907_500,
            "fdv": 4_301_151_702,
            "volume24h": 2_056,
            "price_change_24h": None,
            "buys24h": 2,
            "sells24h": 3,
            "is_known_base_asset": True,
        }
    )

    assert result.rug.status == "LOW"
    assert result.speculation.status == "LOW"
