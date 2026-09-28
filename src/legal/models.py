"""Domain models for the Legal Catalog (Base Jurídica)."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class RuleStatus(str, Enum):
    VERIFICADA = "VERIFICADA"
    PENDIENTE_VALIDACION = "PENDIENTE_VALIDACION"
    SUSTITUIDA = "SUSTITUIDA"


@dataclass(frozen=True)
class LegalRule:
    """Represents a statutory norm, judicial ruling, or administrative rule."""

    rule_id: str
    norma: str
    articulo_o_sentencia: str
    url_oficial: str
    fecha_consulta: date
    periodo_aplicacion: str
    parametros: dict[str, Any]
    interpretacion_implementada: str
    pruebas_asociadas: list[str] = field(default_factory=list)
    estado: RuleStatus = RuleStatus.VERIFICADA
    notas_adicionales: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "norma": self.norma,
            "articulo_o_sentencia": self.articulo_o_sentencia,
            "url_oficial": self.url_oficial,
            "fecha_consulta": self.fecha_consulta.isoformat(),
            "periodo_aplicacion": self.periodo_aplicacion,
            "parametros": self.parametros,
            "interpretacion_implementada": self.interpretacion_implementada,
            "pruebas_asociadas": self.pruebas_asociadas,
            "estado": self.estado.value,
            "notas_adicionales": self.notas_adicionales,
        }
