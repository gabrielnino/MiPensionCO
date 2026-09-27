"""Typed domain models for MiPensiónCO.

Adheres strictly to Clean Code, SOLID, and static type safety.
Uses Decimal for all monetary and fractional week values.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any


class ProvenanceType(str, Enum):
    PDF = "PDF"
    DECLARACION_USUARIO = "DECLARACION_USUARIO"
    CORRECCION_MANUAL = "CORRECCION_MANUAL"
    SUPUESTO = "SUPUESTO"


class AffiliationStatus(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    PENSIONADO = "PENSIONADO"
    DESCONOCIDO = "DESCONOCIDO"


class SexCategory(str, Enum):
    FEMENINO = "FEMENINO"  # Mujer: 57 años
    MASCULINO = "MASCULINO"  # Hombre: 62 años


class TransitionStatus(str, Enum):
    EVIDENCIA_SUFICIENTE_CUMPLIMIENTO = "EVIDENCIA_SUFICIENTE_CUMPLIMIENTO"
    NO_CUMPLE_UMBRAL_CORTE = "NO_CUMPLE_UMBRAL_CORTE"
    INFORMACION_INSUFICIENTE = "INFORMACION_INSUFICIENTE"
    EVALUACION_NO_DEFINITIVA_FECHA_CORTE_FUTURA = (
        "EVALUACION_NO_DEFINITIVA_FECHA_CORTE_FUTURA"
    )
    CASO_JURIDICO_ESPECIAL = "CASO_JURIDICO_ESPECIAL"
    AFILIACION_FUERA_DE_ALCANCE = "AFILIACION_FUERA_DE_ALCANCE"


@dataclass(frozen=True)
class CotizacionRecord:
    """Individual payroll contribution record."""

    periodo_inicio: date
    periodo_fin: date
    dias_reportados: int
    dias_cotizados: int
    ibc: Decimal
    aportante: str
    nit: str = ""
    novedad: str = ""
    observaciones: str = ""
    fecha_pago: date | None = None
    origen: ProvenanceType = ProvenanceType.PDF
    pagina: int = 1
    fila: int = 1
    periodo_mensual_reportado: bool = False
    dias_pendientes_validacion: bool = False
    source_fragment_ids: tuple[str, ...] = ()
    record_id: str = ""
    excluido_del_calculo: bool = False
    motivo_exclusion: str = ""
    motivo_correccion: str = ""
    estado_validacion: str = "VALIDO"
    valor_original: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "periodo_inicio": self.periodo_inicio.isoformat(),
            "periodo_fin": self.periodo_fin.isoformat(),
            "dias_reportados": self.dias_reportados,
            "dias_cotizados": self.dias_cotizados,
            "ibc": float(self.ibc),
            "ibc_exacto": str(self.ibc),
            "aportante": self.aportante,
            "nit": self.nit,
            "novedad": self.novedad,
            "observaciones": self.observaciones,
            "fecha_pago": self.fecha_pago.isoformat() if self.fecha_pago else None,
            "origen": self.origen.value,
            "pagina": self.pagina,
            "fila": self.fila,
            "periodo_mensual_reportado": self.periodo_mensual_reportado,
            "dias_pendientes_validacion": self.dias_pendientes_validacion,
            "source_fragment_ids": list(self.source_fragment_ids),
            "record_id": self.record_id,
            "excluido_del_calculo": self.excluido_del_calculo,
            "motivo_exclusion": self.motivo_exclusion,
            "motivo_correccion": self.motivo_correccion,
            "estado_validacion": self.estado_validacion,
            "valor_original": self.valor_original,
        }


class FieldExtractionStatus(str, Enum):
    EXTRAIDO_PDF = "EXTRAIDO_PDF"
    NO_ENCONTRADO = "NO_ENCONTRADO"
    REQUIERE_REVISION = "REQUIERE_REVISION"
    CORREGIDO_USUARIO = "CORREGIDO_USUARIO"
    DECLARADO_USUARIO = "DECLARADO_USUARIO"


@dataclass(frozen=True)
class ResumenEmpleadorRecord:
    """Documentary summary row per employer from Colpensiones report."""

    nit: str
    nombre_aportante: str
    periodo_inicio: date
    periodo_fin: date
    ultimo_salario: Decimal
    semanas: Decimal
    licencias: Decimal = Decimal(0)
    simultaneidad: Decimal = Decimal(0)
    total_semanas: Decimal = Decimal(0)
    pagina: int = 1
    fila: int = 1
    source_fragment_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "nit": self.nit,
            "nombre_aportante": self.nombre_aportante,
            "periodo_inicio": self.periodo_inicio.isoformat(),
            "periodo_fin": self.periodo_fin.isoformat(),
            "ultimo_salario": float(self.ultimo_salario),
            "ultimo_salario_exacto": str(self.ultimo_salario),
            "semanas": float(self.semanas),
            "licencias": float(self.licencias),
            "simultaneidad": float(self.simultaneidad),
            "total_semanas": float(self.total_semanas),
            "pagina": self.pagina,
            "fila": self.fila,
            "source_fragment_ids": list(self.source_fragment_ids),
        }


@dataclass(frozen=True)
class CorreccionRegistro:
    """Audit log of user-corrected or declared values."""

    campo: str
    valor_original: Any
    valor_corregido: Any
    motivo: str
    procedencia: ProvenanceType


@dataclass
class HistoriaLaboral:
    """Complete labor history extracted from Colpensiones or revised by user."""

    cedula_enmascarada: str
    nombre_enmascarado: str = ""
    fecha_nacimiento: date | None = None
    sexo: SexCategory | None = None
    fecha_afiliacion_colpensiones: date | None = None
    fecha_primera_cotizacion: date | None = None
    fecha_expedicion_reporte: date | None = None
    fecha_actualizacion_reporte: date | None = None
    ultimo_periodo_cotizado: date | None = None
    estado_afiliacion: AffiliationStatus = AffiliationStatus.DESCONOCIDO
    semanas_resumen_colpensiones: Decimal = Decimal(0)
    semanas_alto_riesgo: Decimal | None = None
    tiempos_publicos: Decimal = Decimal(0)
    es_caso_especial: bool = False
    detalle_caso_especial: str = ""
    resumen_empleadores: list[ResumenEmpleadorRecord] = field(default_factory=list)
    registros: list[CotizacionRecord] = field(default_factory=list)
    registros_pendientes: list[dict[str, Any]] = field(default_factory=list)
    periodos_desconocidos_o_faltantes: bool = False
    aportes_posteriores_estado: str = (
        "DESCONOCIDO"  # "SIN_APORTES" | "CON_APORTES" | "DESCONOCIDO"
    )
    correcciones: list[CorreccionRegistro] = field(default_factory=list)
    revision_version: int = 1
    revision_id: str = "rev_initial"
    original_registros: list[CotizacionRecord] = field(default_factory=list)

    def total_dias_cotizados(self) -> int:
        return sum(r.dias_cotizados for r in self.registros)


@dataclass(frozen=True)
class TransitionEvaluation:
    """Legal evaluation of whether the affiliate preserves Ley 100 transition regime."""

    status: TransitionStatus
    umbral_exigido: int
    semanas_acreditadas_al_corte: Decimal
    fecha_corte_aplicada: date
    fuente_juridica: str
    explicacion: str
    permite_continuar_simulacion: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "umbral_exigido": self.umbral_exigido,
            "semanas_acreditadas_al_corte": float(self.semanas_acreditadas_al_corte),
            "fecha_corte_aplicada": self.fecha_corte_aplicada.isoformat(),
            "fuente_juridica": self.fuente_juridica,
            "explicacion": self.explicacion,
            "permite_continuar_simulacion": self.permite_continuar_simulacion,
        }


@dataclass(frozen=True)
class EscenarioConfig:
    """Simulation scenario parameters."""

    escenario_id: str
    nombre: str
    ibc_futuro_inicial: Decimal
    fecha_inicio_ibc: date
    crecimiento_anual_nominal: Decimal = Decimal("0.05")
    periodos_sin_aporte: list[tuple[date, date]] = field(default_factory=list)
    supuesto_inflacion: Decimal = Decimal("0.040")
    supuesto_crecimiento_smlmv: Decimal = Decimal("0.055")
    aportar_hasta_minimo: bool = False


@dataclass(frozen=True)
class SimulationResult:
    """Complete simulation output for an individual scenario."""

    escenario_id: str
    escenario_nombre: str
    fecha_cumplimiento_edad_legal: date
    edad_legal: int
    ya_supero_edad_legal: bool
    semanas_exigidas: int
    semanas_acreditadas_documentales: Decimal
    semanas_recalculadas_calendario: Decimal
    diferencia_semanas_recalculadas: Decimal
    semanas_futuras_proyectadas: Decimal
    semanas_totales_a_la_edad: Decimal
    cumple_semanas: bool
    deficit_semanas: Decimal
    excedente_semanas: Decimal
    ibl_ultimos_10_anos: Decimal | None
    ibl_toda_la_vida: Decimal | None
    metodo_ibl_seleccionado: str | None
    ibl_final: Decimal | None
    smlmv_referencia_retiro: Decimal
    s_factor: Decimal | None
    tasa_reemplazo_inicial_pct: Decimal | None
    semanas_adicionales_computables: Decimal | None
    bloques_completos_50_semanas: int | None
    incremento_tasa_pct: Decimal | None
    tasa_reemplazo_final_pct: Decimal | None
    mesada_bruta: Decimal | None
    limite_aplicado: str | None
    descuento_salud_pct: Decimal | None
    descuento_salud_monto: Decimal | None
    descuento_fsp_pct: Decimal | None
    descuento_fsp_monto: Decimal | None
    valor_despues_descuentos: Decimal | None
    valor_real_poder_adquisitivo: Decimal | None
    equivalente_smlmv: Decimal | None
    mensaje_advertencia: str
    desglose_explicativo: list[str]
    requiere_revision_discrepancia: bool = False
    bloqueado_por_ipc: bool = False
    bloqueado_por_periodo_desconocido: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "escenario_id": self.escenario_id,
            "escenario_nombre": self.escenario_nombre,
            "fecha_cumplimiento_edad_legal": self.fecha_cumplimiento_edad_legal.isoformat(),
            "edad_legal": self.edad_legal,
            "ya_supero_edad_legal": self.ya_supero_edad_legal,
            "semanas_exigidas": self.semanas_exigidas,
            "semanas_acreditadas_documentales": float(
                self.semanas_acreditadas_documentales
            ),
            "semanas_acreditadas_documentales_exacto": str(
                self.semanas_acreditadas_documentales
            ),
            "semanas_recalculadas_calendario": float(
                self.semanas_recalculadas_calendario
            ),
            "semanas_recalculadas_calendario_exacto": str(
                self.semanas_recalculadas_calendario
            ),
            "diferencia_semanas_recalculadas": float(
                self.diferencia_semanas_recalculadas
            ),
            "semanas_futuras_proyectadas": float(self.semanas_futuras_proyectadas),
            "semanas_futuras_proyectadas_exacto": str(self.semanas_futuras_proyectadas),
            "semanas_totales_a_la_edad": float(self.semanas_totales_a_la_edad),
            "semanas_totales_a_la_edad_exacto": str(self.semanas_totales_a_la_edad),
            "cumple_semanas": self.cumple_semanas,
            "deficit_semanas": float(self.deficit_semanas),
            "deficit_semanas_exacto": str(self.deficit_semanas),
            "excedente_semanas": float(self.excedente_semanas),
            "excedente_semanas_exacto": str(self.excedente_semanas),
            "ibl_ultimos_10_anos": float(self.ibl_ultimos_10_anos)
            if self.ibl_ultimos_10_anos
            else None,
            "ibl_ultimos_10_anos_exacto": str(self.ibl_ultimos_10_anos)
            if self.ibl_ultimos_10_anos
            else None,
            "ibl_toda_la_vida": float(self.ibl_toda_la_vida)
            if self.ibl_toda_la_vida
            else None,
            "ibl_toda_la_vida_exacto": str(self.ibl_toda_la_vida)
            if self.ibl_toda_la_vida
            else None,
            "metodo_ibl_seleccionado": self.metodo_ibl_seleccionado,
            "ibl_final": float(self.ibl_final) if self.ibl_final else None,
            "ibl_final_exacto": str(self.ibl_final) if self.ibl_final else None,
            "smlmv_referencia_retiro": float(self.smlmv_referencia_retiro),
            "smlmv_referencia_retiro_exacto": str(self.smlmv_referencia_retiro),
            "s_factor": float(self.s_factor) if self.s_factor else None,
            "tasa_reemplazo_inicial_pct": float(self.tasa_reemplazo_inicial_pct)
            if self.tasa_reemplazo_inicial_pct
            else None,
            "semanas_adicionales_computables": float(
                self.semanas_adicionales_computables
            )
            if self.semanas_adicionales_computables
            else None,
            "bloques_completos_50_semanas": self.bloques_completos_50_semanas,
            "incremento_tasa_pct": float(self.incremento_tasa_pct)
            if self.incremento_tasa_pct
            else None,
            "tasa_reemplazo_final_pct": float(self.tasa_reemplazo_final_pct)
            if self.tasa_reemplazo_final_pct
            else None,
            "mesada_bruta": float(self.mesada_bruta) if self.mesada_bruta else None,
            "mesada_bruta_exacto": str(self.mesada_bruta)
            if self.mesada_bruta
            else None,
            "limite_aplicado": self.limite_aplicado,
            "descuento_salud_pct": float(self.descuento_salud_pct)
            if self.descuento_salud_pct
            else None,
            "descuento_salud_monto": float(self.descuento_salud_monto)
            if self.descuento_salud_monto
            else None,
            "descuento_fsp_pct": float(self.descuento_fsp_pct)
            if self.descuento_fsp_pct
            else None,
            "descuento_fsp_monto": float(self.descuento_fsp_monto)
            if self.descuento_fsp_monto
            else None,
            "valor_despues_descuentos": float(self.valor_despues_descuentos)
            if self.valor_despues_descuentos
            else None,
            "valor_despues_descuentos_exacto": str(self.valor_despues_descuentos)
            if self.valor_despues_descuentos
            else None,
            "valor_real_poder_adquisitivo": float(self.valor_real_poder_adquisitivo)
            if self.valor_real_poder_adquisitivo
            else None,
            "equivalente_smlmv": float(self.equivalente_smlmv)
            if self.equivalente_smlmv
            else None,
            "mensaje_advertencia": self.mensaje_advertencia,
            "desglose_explicativo": self.desglose_explicativo,
            "requiere_revision_discrepancia": self.requiere_revision_discrepancia,
            "bloqueado_por_ipc": self.bloqueado_por_ipc,
            "bloqueado_por_periodo_desconocido": self.bloqueado_por_periodo_desconocido,
        }
