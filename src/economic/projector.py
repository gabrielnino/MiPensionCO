"""Economic Projector & Purchasing Power Converter.

Ensures clear separation between official historical observations and future economic assumptions.
Prevents double-counting inflation.
"""

from dataclasses import dataclass
from decimal import Decimal

from src.economic.ipc import calculate_ipc_adjustment_factor
from src.economic.smlmv import get_smlmv


@dataclass(frozen=True)
class EconomicAssumptions:
    """Parameters for future economic projections."""

    assumed_annual_inflation: Decimal = Decimal(
        "0.040"
    )  # 4.0% default long-term Banco de la República target
    assumed_annual_smlmv_growth: Decimal = Decimal(
        "0.055"
    )  # 5.5% default nominal minimum wage growth
    base_year: int = 2026
    base_month: int = 8


@dataclass(frozen=True)
class ValuationResult:
    """Monetary amounts expressed in nominal, real, and SMLMV terms."""

    nominal_cop: Decimal
    real_base_cop: Decimal
    smlmv_projected_amount: Decimal
    smlmv_multiples: Decimal


class EconomicProjector:
    """Handles economic projections and currency conversions."""

    def __init__(self, assumptions: EconomicAssumptions | None = None) -> None:
        self.assumptions = assumptions or EconomicAssumptions()

    def get_projected_smlmv(self, target_year: int) -> Decimal:
        """Returns official SMLMV if target_year <= 2026, otherwise projects forward."""
        if target_year <= 2026:
            return get_smlmv(target_year).monthly_amount

        # Compounded growth from 2026 baseline
        baseline_2026 = get_smlmv(2026).monthly_amount
        years_ahead = target_year - 2026
        factor = (Decimal(1) + self.assumptions.assumed_annual_smlmv_growth) ** Decimal(
            years_ahead
        )
        return (baseline_2026 * factor).quantize(Decimal(1))

    def convert_valuation(
        self,
        nominal_amount: Decimal,
        target_year: int,
        target_month: int,
    ) -> ValuationResult:
        """Converts a nominal future amount into real base purchasing power and SMLMV multiples."""
        smlmv_target = self.get_projected_smlmv(target_year)
        smlmv_multiples = (nominal_amount / smlmv_target).quantize(Decimal("0.0001"))

        # Deflate from target date to base date (August 2026) to obtain real purchasing power
        # Factor is IPC(target) / IPC(base), so real_cop = nominal / factor
        ipc_factor = calculate_ipc_adjustment_factor(
            initial_year=self.assumptions.base_year,
            initial_month=self.assumptions.base_month,
            target_year=target_year,
            target_month=target_month,
            assumed_annual_inflation=self.assumptions.assumed_annual_inflation,
        )
        real_base_cop = (nominal_amount / ipc_factor).quantize(Decimal(1))

        return ValuationResult(
            nominal_cop=nominal_amount.quantize(Decimal(1)),
            real_base_cop=real_base_cop,
            smlmv_projected_amount=smlmv_target,
            smlmv_multiples=smlmv_multiples,
        )
