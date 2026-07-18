"""Transaction cost models for realistic backtesting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CostResult:
    """Estimated fees for a single trade."""

    commission: Decimal
    impact: Decimal
    slippage: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.commission + self.impact + self.slippage


@dataclass
class SimpleCostModel:
    """
    Commission in bps of notional plus optional market-impact
    scaled by participation rate (notional / ADV).
    """

    commission_bps: float = 5.0
    impact_bps_per_participation: float = 0.0
    slippage_bps: float = 0.0

    def estimate(
        self,
        notional: Decimal | float | int,
        adv_notional: Decimal | float | int | None = None,
        side: str = "buy",
    ) -> CostResult:
        notional_d = Decimal(str(notional))
        if notional_d < 0:
            notional_d = -notional_d

        commission = notional_d * Decimal(str(self.commission_bps)) / Decimal("10000")
        slippage = notional_d * Decimal(str(self.slippage_bps)) / Decimal("10000")

        impact = Decimal("0")
        if (
            self.impact_bps_per_participation > 0
            and adv_notional is not None
            and Decimal(str(adv_notional)) > 0
        ):
            adv = Decimal(str(adv_notional))
            participation = float(notional_d / adv)
            # clamp extreme participation for stability
            participation = max(0.0, min(participation, 5.0))
            impact_bps = self.impact_bps_per_participation * participation
            impact = notional_d * Decimal(str(impact_bps)) / Decimal("10000")

        return CostResult(commission=commission, impact=impact, slippage=slippage)
