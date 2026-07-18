"""Walk-forward API routes."""

from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from quant_lab_api.database.base import get_db
from quant_lab_api.services.backtest_service import BacktestService
from quant_lab_api.repositories.experiment_repository import ExperimentRepository

router = APIRouter(prefix="/api/backtest", tags=["walk-forward"])


class WalkForwardRequest(BaseModel):
    strategy_name: str
    tickers: list[str] = Field(..., min_length=1)
    start_date: str
    end_date: str
    initial_capital: float = Field(default=100000.0, gt=0)
    commission_bps: float = Field(default=5.0, ge=0)
    slippage_bps: float = Field(default=2.0, ge=0)
    impact_bps: float = Field(default=0.0, ge=0)
    rebalance_frequency: int = Field(default=5, gt=0)
    provider: Literal["csv", "yahoo"] = "csv"
    train_days: int = Field(default=60, gt=0)
    test_days: int = Field(default=20, gt=0)
    step_days: int = Field(default=20, gt=0)
    mode: Literal["rolling", "expanding"] = "rolling"
    save_experiment: bool = True
    sizer: Literal["percent", "vol_target", "equal_weight"] = "percent"
    max_position_pct: float = Field(default=0.20, gt=0, le=1)
    target_vol: float = Field(default=0.10, gt=0)
    max_gross_leverage: float = Field(default=2.0, gt=0)
    max_drawdown_halt: float = Field(default=0.30, gt=0, le=1)
    enable_risk_gate: bool = True
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    time_stop_days: int | None = None
    resize_signals: bool = False


@router.post("/walk-forward")
async def run_walk_forward(
    request: WalkForwardRequest,
    db: Session = Depends(get_db),
) -> dict:
    service = BacktestService()
    try:
        report = await service.run_walk_forward(
            strategy_name=request.strategy_name,
            tickers=request.tickers,
            start_date=date.fromisoformat(request.start_date),
            end_date=date.fromisoformat(request.end_date),
            initial_capital=request.initial_capital,
            commission_bps=request.commission_bps,
            slippage_bps=request.slippage_bps,
            impact_bps=request.impact_bps,
            rebalance_frequency=request.rebalance_frequency,
            provider=request.provider,
            train_days=request.train_days,
            test_days=request.test_days,
            step_days=request.step_days,
            mode=request.mode,
            sizer=request.sizer,
            max_position_pct=request.max_position_pct,
            target_vol=request.target_vol,
            max_gross_leverage=request.max_gross_leverage,
            max_drawdown_halt=request.max_drawdown_halt,
            enable_risk_gate=request.enable_risk_gate,
            stop_loss_pct=request.stop_loss_pct,
            take_profit_pct=request.take_profit_pct,
            time_stop_days=request.time_stop_days,
            resize_signals=request.resize_signals,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if request.save_experiment:
        ExperimentRepository(db).create(
            kind="walk_forward",
            strategy_name=report.get("strategy_name", request.strategy_name),
            name=f"WF {request.strategy_name} {request.start_date}→{request.end_date}",
            params=request.model_dump(),
            metrics=report.get("aggregate"),
            artifact={"n_folds": report.get("aggregate", {}).get("n_folds"), "folds": report.get("folds")},
        )

    return report
