"""Colpensiones Labor History PDF Reader & Extractor.

Uses PyMuPDF (fitz) for pure local, offline extraction.
Does not log passwords or send data externally.
Adheres strictly to Colombian formatting (DD/MM/YYYY, COP currency).
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import fitz  # type: ignore[import-untyped]  # PyMuPDF

from src.domain.models import (
    AffiliationStatus,
    CotizacionRecord,
    HistoriaLaboral,
    ProvenanceType,
    SexCategory,
)


class PDFSecurityError(Exception):
    """Raised when PDF is encrypted and requires a password."""


class PDFCorruptError(Exception):
    """Raised when PDF file is invalid, corrupt, or unrecognizable."""


class PDFExtractionError(Exception):
    """Raised when parsing fails or document has missing/inconsistent pages."""


@dataclass
class ParseReport:
    success: bool
    requires_password: bool = False
    error_message: str | None = None
    pages_processed: int = 0
    records_extracted: int = 0
    warnings: list[str] = None  # type: ignore

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


class ColpensionesPDFReader:
    """Robust local parser for Colpensiones labor history reports."""

    DATE_PATTERN = re.compile(r"(\d{2})[/.-](\d{2})[/.-](\d{4})")
    MONEY_PATTERN = re.compile(
        r"[\$]?\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)"
    )

    @classmethod
    def parse_colombian_date(cls, text: str) -> date | None:
        """Parses dates in DD/MM/YYYY or YYYY-MM-DD formats."""
        text = text.strip()
        m = cls.DATE_PATTERN.search(text)
        if m:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                pass
        # Try ISO
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass
        return None

    @classmethod
    def parse_colombian_decimal(cls, text: str) -> Decimal:
        """Parses Colombian currency or number strings (e.g. 1.234.567,50 or 1,234,567.50)."""
        clean = text.replace("$", "").replace("COP", "").strip()
        if not clean:
            return Decimal(0)

        # If both '.' and ',' appear
        if "." in clean and "," in clean:
            if clean.rfind(",") > clean.rfind("."):
                # 1.234.567,89 -> remove dots, replace comma with dot
                clean = clean.replace(".", "").replace(",", ".")
            else:
                # 1,234,567.89 -> remove commas
                clean = clean.replace(",", "")
        elif "," in clean:
            # Check if comma is decimal separator (e.g. 910,43) or thousands
            parts = clean.split(",")
            if len(parts) == 2 and len(parts[1]) in (1, 2):
                clean = parts[0] + "." + parts[1]
            else:
                clean = clean.replace(",", "")
        elif "." in clean:
            # Check if dot is thousands separator (1.234.567) or decimal (910.43)
            parts = clean.split(".")
            if len(parts) != 2 or len(parts[1]) not in (1, 2):
                clean = clean.replace(".", "")

        try:
            return Decimal(clean)
        except (ValueError, ArithmeticError):
            return Decimal(0)

    @classmethod
    def extract_from_bytes(
        cls,
        pdf_bytes: bytes,
        password: str | None = None,
    ) -> tuple[HistoriaLaboral | None, ParseReport]:
        """Parses Colpensiones PDF directly from in-memory byte buffer."""
        report = ParseReport(success=False)

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except (RuntimeError, ValueError) as exc:
            report.error_message = f"Archivo corrupto o formato no reconocido: {exc}"
            return None, report

        # 1. Password check
        if doc.is_encrypted:
            if not password:
                report.requires_password = True
                report.error_message = "El archivo PDF está protegido con contraseña."
                doc.close()
                return None, report
            auth_ok = doc.authenticate(password)
            if not auth_ok:
                report.requires_password = True
                report.error_message = "Contraseña incorrecta."
                doc.close()
                return None, report

        if doc.page_count == 0:
            report.error_message = "El archivo PDF no contiene páginas."
            doc.close()
            return None, report

        report.pages_processed = doc.page_count

        historia = HistoriaLaboral(cedula_enmascarada="ANON-XXXXX")
        records: list[CotizacionRecord] = []

        total_text = ""
        for page_idx in range(doc.page_count):
            page = doc[page_idx]
            page_text = page.get_text("text")
            total_text += page_text + "\n"

            # Parse lines on page
            lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]

            # Look for contribution table rows
            # Pattern: StartDate EndDate Days IBC Employer
            for row_idx, line in enumerate(lines):
                dates_found = cls.DATE_PATTERN.findall(line)
                if len(dates_found) >= 2:
                    d1_str = (
                        f"{dates_found[0][0]}/{dates_found[0][1]}/{dates_found[0][2]}"
                    )
                    d2_str = (
                        f"{dates_found[1][0]}/{dates_found[1][1]}/{dates_found[1][2]}"
                    )
                    p_start = cls.parse_colombian_date(d1_str)
                    p_end = cls.parse_colombian_date(d2_str)

                    if p_start and p_end:
                        # Extract numbers from line
                        numbers = re.findall(r"\b\d+(?:[.,]\d+)?\b", line)
                        # Assume days is the 3rd or 4th integer, IBC is the largest number
                        days = 30
                        ibc = Decimal(1300000)
                        for num in numbers:
                            val = cls.parse_colombian_decimal(num)
                            if 1 <= val <= 31 and days == 30:
                                days = int(val)
                            elif val > Decimal(100000):
                                ibc = val

                        # Remaining tokens as employer
                        employer = "EMPLEADOR REPORTADO"
                        words = [
                            w for w in line.split() if not any(c.isdigit() for c in w)
                        ]
                        if words:
                            employer = " ".join(words[:4])

                        rec = CotizacionRecord(
                            periodo_inicio=p_start,
                            periodo_fin=p_end,
                            dias_reportados=days,
                            dias_cotizados=days,
                            ibc=ibc,
                            aportante=employer,
                            origen=ProvenanceType.PDF,
                            pagina=page_idx + 1,
                            fila=row_idx + 1,
                        )
                        records.append(rec)

        # Extract metadata from total text
        # Birth date
        m_birth = re.search(
            r"(?:Fecha\s+de\s+Nacimiento|Nacimiento)[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})",
            total_text,
            re.IGNORECASE,
        )
        if m_birth:
            historia.fecha_nacimiento = cls.parse_colombian_date(m_birth.group(1))

        # Sex / Category
        m_sex = re.search(
            r"(?:Sexo|G[eé]nero)[:\s]+(FEMENINO|MASCULINO|MUJER|HOMBRE|F|M)\b",
            total_text,
            re.IGNORECASE,
        )
        if m_sex:
            val_s = m_sex.group(1).upper()
            if val_s in ("FEMENINO", "MUJER", "F"):
                historia.sexo = SexCategory.FEMENINO
            elif val_s in ("MASCULINO", "HOMBRE", "M"):
                historia.sexo = SexCategory.MASCULINO

        # Report date
        m_exp = re.search(
            r"(?:Fecha\s+de\s+Expedici[oó]n|Expedici[oó]n|Actualizaci[oó]n)[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})",
            total_text,
            re.IGNORECASE,
        )
        if m_exp:
            historia.fecha_actualizacion_reporte = cls.parse_colombian_date(
                m_exp.group(1)
            )
            historia.fecha_expedicion_reporte = historia.fecha_actualizacion_reporte

        # Colpensiones summary recognized weeks
        m_weeks = re.search(
            r"(?:Total\s+Semanas|Semanas\s+Cotizadas|Total\s+de\s+semanas)[:\s]+([0-9.,]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_weeks:
            historia.semanas_resumen_colpensiones = cls.parse_colombian_decimal(
                m_weeks.group(1)
            )

        # High risk weeks
        m_hr = re.search(
            r"(?:Alto\s+Riesgo|Semanas\s+de\s+Alto\s+Riesgo)[:\s]+([0-9.,]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_hr:
            historia.semanas_alto_riesgo = cls.parse_colombian_decimal(m_hr.group(1))
            if historia.semanas_alto_riesgo > Decimal(0):
                historia.es_caso_especial = True
                historia.detalle_caso_especial = f"Registra {historia.semanas_alto_riesgo} semanas de alto riesgo (Decreto 2090 de 2003)."

        # Affiliation status
        if re.search(r"\bPENSIONADO\b", total_text, re.IGNORECASE):
            historia.estado_afiliacion = AffiliationStatus.PENSIONADO
        elif re.search(r"\bACTIVO\b", total_text, re.IGNORECASE):
            historia.estado_afiliacion = AffiliationStatus.ACTIVO
        elif re.search(r"\bINACTIVO\b", total_text, re.IGNORECASE):
            historia.estado_afiliacion = AffiliationStatus.INACTIVO

        # Affiliation date vs first cotizacion
        m_af = re.search(
            r"(?:Fecha\s+de\s+Afiliaci[oó]n)[:\s]+(\d{2}[/.-]\d{2}[/.-]\d{4})",
            total_text,
            re.IGNORECASE,
        )
        if m_af:
            historia.fecha_afiliacion_colpensiones = cls.parse_colombian_date(
                m_af.group(1)
            )

        if records:
            historia.fecha_primera_cotizacion = min(r.periodo_inicio for r in records)

        historia.registros = records
        report.records_extracted = len(records)
        report.success = True

        doc.close()
        return historia, report
