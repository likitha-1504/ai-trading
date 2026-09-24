"""Market scanner and indicator feature endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_db_repo
from app.api.schemas import MarketScannerItem
from app.db.repository import DatabaseRepository
from app.models.contracts import FeatureSnapshot

router = APIRouter()


@router.get(
    "/scanner",
    response_model=list[MarketScannerItem],
    summary="Get active market scanner telemetry",
    description="Returns latest price, VWAP, relative volume, momentum, and regime for tracked instruments.",
)
def get_market_scanner(
    repo: DatabaseRepository = Depends(get_db_repo),
) -> list[MarketScannerItem]:
    features = repo.get_all_latest_features()
    items: list[MarketScannerItem] = []
    for f in features:
        items.append(
            MarketScannerItem(
                symbol=f.symbol,
                price=f.current_price,
                vwap=f.vwap,
                relative_volume=f.relative_volume_10,
                momentum_score=f.momentum_score,
                spread_pct=f.spread_pct,
                liquidity_score=f.liquidity_score,
                regime=f.regime,
                timestamp=f.timestamp,
            )
        )
    return items


@router.get(
    "/features/{symbol}",
    response_model=FeatureSnapshot,
    summary="Get latest quantitative feature snapshot for symbol",
    description="Returns computed multi-timeframe indicators, volume acceleration, price acceleration, and regime.",
)
def get_features_for_symbol(
    symbol: str,
    repo: DatabaseRepository = Depends(get_db_repo),
) -> FeatureSnapshot:
    feat = repo.get_latest_feature(symbol.upper())
    if not feat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No feature snapshot available for symbol {symbol.upper()}",
        )
    return feat
