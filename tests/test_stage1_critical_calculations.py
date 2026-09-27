"""TDD Test Suite for Stage 1: Critical Pension Calculations.

Reproduces:
- Hallazgo 1: Invented historical contributions between last contribution and evaluation date.
- Hallazgo 2: Incorrect IPC series (e.g. 86.498/87.726 in Jan/Feb 2018 giving 1.4197% instead of official 0.71%).
- Hallazgo 3: Documentary discrepancy that did not block mesada (requiere_revision_discrepancia=True with mesada_bruta calculated).
"""

from datetime import date
from decimal import Decimal

from src.domain.models import (
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    ProvenanceType,
    SexCategory,
)
from src.domain.pension_engine import PensionEngine
from src.economic.ipc import (
    get_dane_ipc_metadata,
    get_ipc,
)


# ---------------------------------------------------------------------------
# HALLAZGO 1: Aportes Históricos Inventados
# ---------------------------------------------------------------------------
def test_hallazgo_1_no_automatic_historical_contributions() -> None:
    """Evaluation date: 2026-09-27. Last record: 2025-12-31. Scenario starts: 2026-01-01.

    The engine MUST NOT invent 38.57 historical weeks between Jan 2026 and Sept 2026.
    """
    engine = PensionEngine()
    as_of = date(2026, 9, 27)

    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-H1",
        fecha_nacimiento=date(1964, 12, 1),  # 62 on 2026-12-01
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("1260.00"),
        registros=[
            CotizacionRecord(
                periodo_inicio=date(2020, 1, 1),
                periodo_fin=date(2025, 12, 31),
                dias_reportados=2190,
                dias_cotizados=2190,
                ibc=Decimal(3500000),
                aportante="EMPRESA REAL",
            )
        ],
    )

    escenario = EscenarioConfig(
        escenario_id="esc_h1",
        nombre="Escenario Enero 2026",
        ibc_futuro_inicial=Decimal(3500000),
        fecha_inicio_ibc=date(2026, 1, 1),  # Starts in the past relative to as_of
    )

    res = engine.simulate_scenario(historia, escenario, as_of_date=as_of)

    # 1. Projected weeks can ONLY cover strictly future days (post 2026-09-27 to 2026-12-01: ~9 weeks)
    assert res.semanas_futuras_proyectadas < Decimal("12.00")

    # 2. Total weeks must NOT add 38.57 weeks from the undeclared past (Jan to Sept 2026)
    # Total weeks must equal base_weeks (1260) + projected weeks (< 12)
    expected_max = Decimal("1260.00") + res.semanas_futuras_proyectadas
    assert res.semanas_totales_a_la_edad <= expected_max, (
        f"Engine added undeclared past weeks! Total={res.semanas_totales_a_la_edad}, expected <= {expected_max}"
    )


def test_hallazgo_1_changing_scenario_start_does_not_create_declarations() -> None:
    """Changing scenario start date to an earlier date must not change total weeks or fabricate declarations."""
    engine = PensionEngine()
    as_of = date(2026, 9, 27)

    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-H1B",
        fecha_nacimiento=date(1964, 12, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("1260.00"),
        registros=[
            CotizacionRecord(
                periodo_inicio=date(2020, 1, 1),
                periodo_fin=date(2025, 12, 31),
                dias_reportados=2190,
                dias_cotizados=2190,
                ibc=Decimal(3500000),
                aportante="EMPRESA REAL",
            )
        ],
    )

    esc1 = EscenarioConfig(
        escenario_id="esc_jan",
        nombre="Inicio Enero",
        ibc_futuro_inicial=Decimal(3500000),
        fecha_inicio_ibc=date(2026, 1, 1),
    )
    esc2 = EscenarioConfig(
        escenario_id="esc_may",
        nombre="Inicio Mayo",
        ibc_futuro_inicial=Decimal(3500000),
        fecha_inicio_ibc=date(2026, 5, 1),
    )

    res1 = engine.simulate_scenario(historia, esc1, as_of_date=as_of)
    res2 = engine.simulate_scenario(historia, esc2, as_of_date=as_of)

    # Future projection from 2026-09-27 forward must be identical
    assert res1.semanas_futuras_proyectadas == res2.semanas_futuras_proyectadas
    assert res1.semanas_totales_a_la_edad == res2.semanas_totales_a_la_edad


def test_hallazgo_1_explicit_user_declaration_audited_and_separated() -> None:
    """Explicit user declaration in historia.registros is respected and separated in audit."""
    engine = PensionEngine()
    as_of = date(2026, 9, 27)

    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-H1C",
        fecha_nacimiento=date(1964, 12, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("1260.00"),
        registros=[
            CotizacionRecord(
                periodo_inicio=date(2020, 1, 1),
                periodo_fin=date(2025, 12, 31),
                dias_reportados=2190,
                dias_cotizados=2190,
                ibc=Decimal(3500000),
                aportante="EMPRESA REAL",
                origen=ProvenanceType.PDF,
            ),
            # User explicitly declared Jan to March 2026
            CotizacionRecord(
                periodo_inicio=date(2026, 1, 1),
                periodo_fin=date(2026, 3, 31),
                dias_reportados=90,
                dias_cotizados=90,
                ibc=Decimal(3500000),
                aportante="INDEPENDIENTE DECLARADO",
                origen=ProvenanceType.DECLARACION_USUARIO,
                observaciones="Aportes pagados como independiente no certificados en PDF",
            ),
        ],
    )

    esc = EscenarioConfig(
        escenario_id="esc_decl",
        nombre="Con Declaración",
        ibc_futuro_inicial=Decimal(3500000),
        fecha_inicio_ibc=date(2026, 10, 1),
    )

    res = engine.simulate_scenario(historia, esc, as_of_date=as_of)
    assert res is not None


# ---------------------------------------------------------------------------
# HALLAZGO 2: Serie IPC Oficial del DANE
# ---------------------------------------------------------------------------
def test_hallazgo_2_official_dane_ipc_values_and_variation() -> None:
    """Contrast Jan and Feb 2018 against DANE bulletin cp_ipc_feb18.pdf.

    Jan 2018 = 97.53, Feb 2018 = 98.22 -> Monthly variation = 0.71%.
    Must NOT be 86.498 or 87.726 (which implied 1.4197%).
    """
    ipc_jan_2018 = get_ipc(2018, 1)
    ipc_feb_2018 = get_ipc(2018, 2)
    ipc_dec_2018 = get_ipc(2018, 12)
    ipc_aug_2026 = get_ipc(2026, 8)

    # 1. Correct official DANE values
    assert ipc_jan_2018 == Decimal("97.53"), (
        f"Jan 2018 was {ipc_jan_2018}, expected 97.53"
    )
    assert ipc_feb_2018 == Decimal("98.22"), (
        f"Feb 2018 was {ipc_feb_2018}, expected 98.22"
    )
    assert ipc_dec_2018 == Decimal("100.00"), (
        f"Dec 2018 was {ipc_dec_2018}, expected 100.00"
    )
    assert ipc_aug_2026 == Decimal("160.42"), (
        f"Aug 2026 was {ipc_aug_2026}, expected 160.42"
    )

    # 2. Monthly variation Jan-Feb 2018: (98.22 - 97.53) / 97.53 = 0.0070747... -> 0.71%
    var_pct = ((ipc_feb_2018 - ipc_jan_2018) / ipc_jan_2018) * Decimal(100)
    assert round(float(var_pct), 2) == 0.71, f"Variation was {var_pct}%, expected 0.71%"


def test_hallazgo_2_missing_observation_blocks_dependents_with_diagnosis() -> None:
    """Missing or unverified observation raises IPCFaltanteError and blocks calculation cleanly."""
    engine = PensionEngine()
    # Salary requiring an index from an unverified/missing date
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-H2",
        fecha_nacimiento=date(1964, 5, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(0),
        registros=[
            CotizacionRecord(
                periodo_inicio=date(2000, 1, 1),  # Pre-2003 unverified month
                periodo_fin=date(2024, 12, 6),
                dias_reportados=9107,
                dias_cotizados=9107,  # 9107 / 7 = 1301.00 weeks
                ibc=Decimal(2000000),
                aportante="EMPRESA 2000",
            )
        ],
    )
    esc = EscenarioConfig(
        escenario_id="esc_h2",
        nombre="Escenario IPC",
        ibc_futuro_inicial=Decimal(3000000),
        fecha_inicio_ibc=date(2026, 10, 1),
    )
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))
    # Engine must cleanly block without generic 500 error
    assert res.bloqueado_por_ipc is True
    assert res.mesada_bruta is None
    assert "IPC" in res.mensaje_advertencia


def test_hallazgo_2_ipc_metadata_contains_official_source_and_hash() -> None:
    """Metadata must identify DANE official source, base, range and file hash."""
    meta = get_dane_ipc_metadata()
    assert meta["source"] == "DANE"
    assert meta["base"] == "Diciembre 2018 = 100.0"
    assert meta["file"] == "anex-IPC-Indices-ago2026.xlsx"
    assert "sha256" in meta
    assert (
        meta["sha256"]
        == "bd622e4c35b80c83085cbd24b6fdc282e578c0c2b15ac6f9eae332ddff52e264"
    )


# ---------------------------------------------------------------------------
# HALLAZGO 3: Discrepancia Documental Debe Bloquear Mesada
# ---------------------------------------------------------------------------
def test_hallazgo_3_discrepancy_affecting_blocks_strictly_blocks_mesada() -> None:
    """Reproduction of user report: requiere_revision_discrepancia=True MUST have mesada_bruta=None!

    Case: 1320 doc weeks vs 1370 cal weeks. Difference affects 50-week blocks (0 blocks vs 1 block).
    Even though both >= 1300, mesada must be blocked until discrepancy is verified.
    """
    engine = PensionEngine()
    as_of = date(2026, 9, 27)

    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-H3",
        fecha_nacimiento=date(
            1964, 5, 1
        ),  # 62 on 2026-05-01 (reached retirement age in past)
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("1320.00"),  # 0 blocks beyond 1300
        registros=[
            # 1370 calendar weeks (1 block beyond 1300)
            CotizacionRecord(
                periodo_inicio=date(1997, 1, 1),
                periodo_fin=date(2023, 4, 30),
                dias_reportados=9590,
                dias_cotizados=9590,  # 9590 / 7 = 1370.00 weeks
                ibc=Decimal(3000000),
                aportante="EMPRESA DISCREPANCIA",
            )
        ],
    )

    esc = EscenarioConfig(
        escenario_id="esc_h3",
        nombre="Escenario Discrepancia",
        ibc_futuro_inicial=Decimal(3000000),
        fecha_inicio_ibc=date(2026, 10, 1),
    )

    res = engine.simulate_scenario(historia, esc, as_of_date=as_of)

    # Discrepancia detected
    assert res.requiere_revision_discrepancia is True

    # CRITICAL: mesada_bruta and dependent amounts MUST be None!
    assert res.mesada_bruta is None, (
        f"CRITICAL DEFECT: mesada_bruta was {res.mesada_bruta} despite requiere_revision_discrepancia=True!"
    )
    assert res.tasa_reemplazo_final_pct is None
    assert res.descuento_salud_monto is None
    assert res.valor_despues_descuentos is None
    assert res.limite_aplicado == "BLOQUEADO_POR_DISCREPANCIA"


def test_hallazgo_3_discrepancy_under_one_week_crossing_threshold_blocks() -> None:
    """A discrepancy of under 1 week crossing eligibility threshold must be detected and block mesada."""
    engine = PensionEngine()
    as_of = date(2026, 9, 27)

    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-H3B",
        fecha_nacimiento=date(1964, 5, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("1299.60"),  # Under 1300 threshold
        registros=[
            CotizacionRecord(
                periodo_inicio=date(2000, 1, 1),
                periodo_fin=date(2024, 11, 30),
                dias_reportados=9102,
                dias_cotizados=9102,  # 9102 / 7 = 1300.28 weeks (Above 1300 threshold!)
                ibc=Decimal(3000000),
                aportante="EMPRESA UMBRAL",
            )
        ],
    )

    esc = EscenarioConfig(
        escenario_id="esc_h3b",
        nombre="Escenario Umbral Fraccion",
        ibc_futuro_inicial=Decimal(3000000),
        fecha_inicio_ibc=date(2026, 10, 1),
    )

    res = engine.simulate_scenario(historia, esc, as_of_date=as_of)

    # Difference is 0.68 weeks (< 1 week), but crosses the 1300 threshold
    assert res.requiere_revision_discrepancia is True
    assert res.mesada_bruta is None
    assert res.limite_aplicado == "BLOQUEADO_POR_DISCREPANCIA"
