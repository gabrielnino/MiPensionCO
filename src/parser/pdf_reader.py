"""Colpensiones Labor History PDF Reader & Extractor.

Uses PyMuPDF (fitz) for pure local, offline extraction.
Does not log passwords or send data externally.
Adheres strictly to Colombian formatting (DD/MM/YYYY, COP currency).
Integrates with AuditService for step-by-step extraction audit.
"""

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

import fitz  # type: ignore[import-untyped]  # PyMuPDF

from src.audit.models import (
    AuditSeverity,
    AuditStep,
    DataFieldAudit,
    EventCode,
    PageExtractionAudit,
)
from src.audit.service import AuditService
from src.domain.models import (
    AffiliationStatus,
    CotizacionRecord,
    FieldExtractionStatus,
    HistoriaLaboral,
    ProvenanceType,
    ResumenEmpleadorRecord,
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
    execution_id: str = ""

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


class ColpensionesPDFReader:
    """Robust local parser for Colpensiones labor history reports."""

    SPANISH_MONTHS: ClassVar[dict[str, int]] = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }
    DATE_TEXTUAL_PATTERN = re.compile(
        r"(\d{1,2})(?:\s+de|\s*-|\s+)(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)(?:\s+de|\s*-|\s+)(\d{4})",
        re.IGNORECASE,
    )
    DATE_PATTERN = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})")
    MONEY_TOKEN_PATTERN = re.compile(
        r"[\$]?\s*([0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{2})?|[0-9]{5,}(?:,[0-9]{2})?)"
    )
    DAYS_PATTERN = re.compile(r"\b([1-9]|[12]\d|3[01])\b")

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitizes text by removing non-printable control characters while preserving plain string content."""
        clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        return clean.strip()

    @classmethod
    def parse_colombian_date(cls, text: str) -> date | None:
        """Parses dates in DD/MM/YYYY, textual Spanish ('30 agosto 2025', '30 de agosto de 2025'), or YYYY-MM-DD formats."""
        clean = text.strip()
        # 1. Textual match first (e.g. 30 agosto 2025 or 30 de agosto de 2025)
        m_txt = cls.DATE_TEXTUAL_PATTERN.search(clean)
        if m_txt:
            day = int(m_txt.group(1))
            month_str = m_txt.group(2).lower()
            year = int(m_txt.group(3))
            month = cls.SPANISH_MONTHS.get(month_str)
            if month:
                try:
                    return date(year, month, day)
                except ValueError:
                    pass

        # 2. Numerical DD/MM/YYYY
        m_num = cls.DATE_PATTERN.search(clean)
        if m_num:
            day, month, year = (
                int(m_num.group(1)),
                int(m_num.group(2)),
                int(m_num.group(3)),
            )
            try:
                return date(year, month, day)
            except ValueError:
                pass

        # 3. ISO format
        try:
            return date.fromisoformat(clean)
        except ValueError:
            pass
        return None

    @classmethod
    def parse_colombian_decimal(cls, text: str) -> Decimal:
        """Parses Colombian currency or number strings (e.g. 3.000.000 or 1,234,567.50)."""
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
            parts = clean.split(",")
            if len(parts) == 2 and len(parts[1]) in (1, 2):
                clean = parts[0] + "." + parts[1]
            else:
                clean = clean.replace(",", "")
        elif "." in clean:
            parts = clean.split(".")
            # If standard Colombian thousands dot (e.g. 3.000.000 or 150.000)
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
                clean = clean.replace(".", "")
            elif len(parts) == 2 and len(parts[1]) in (1, 2):
                pass  # Decimal point (e.g. 910.43)
            else:
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
        execution_id: str | None = None,
    ) -> tuple[HistoriaLaboral | None, ParseReport]:
        """Parses Colpensiones PDF directly from in-memory byte buffer."""
        exec_id = execution_id or str(uuid.uuid4())
        report = ParseReport(success=False, execution_id=exec_id)
        audit = AuditService.get_or_create_audit(exec_id)
        audit.document_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except (RuntimeError, ValueError) as exc:
            report.error_message = (
                f"PDF_CORRUPTO: Archivo corrupto o formato no reconocido: {exc}"
            )
            AuditService.log_technical(
                exec_id,
                AuditStep.EXTRACCION_PDF,
                "ColpensionesPDFReader",
                0.0,
                AuditSeverity.ERROR,
                EventCode.PDF_CORRUPTO,
                "ERROR",
                str(exc),
                "Verificar integridad del archivo",
            )
            return None, report

        # 1. Password check
        if doc.is_encrypted:
            if not password:
                report.requires_password = True
                report.error_message = (
                    "PDF_PROTEGIDO_CLAVE: El archivo PDF está protegido con contraseña."
                )
                AuditService.log_technical(
                    exec_id,
                    AuditStep.EXTRACCION_PDF,
                    "ColpensionesPDFReader",
                    0.0,
                    AuditSeverity.ADVERTENCIA,
                    EventCode.PDF_PROTEGIDO_CLAVE,
                    "BLOQUEADO",
                    "Requiere clave",
                    "Solicitar clave localmente",
                )
                doc.close()
                return None, report
            auth_ok = doc.authenticate(password)
            if not auth_ok:
                report.requires_password = True
                report.error_message = "PDF_PROTEGIDO_CLAVE: Contraseña incorrecta."
                AuditService.log_technical(
                    exec_id,
                    AuditStep.EXTRACCION_PDF,
                    "ColpensionesPDFReader",
                    0.0,
                    AuditSeverity.ADVERTENCIA,
                    EventCode.PDF_PROTEGIDO_CLAVE,
                    "BLOQUEADO",
                    "Clave no válida",
                    "Solicitar clave correcta",
                )
                doc.close()
                return None, report

        if doc.page_count == 0:
            report.error_message = "PDF_VACIO: El archivo PDF no contiene páginas."
            audit.extraction_status = "INCOMPLETA"
            doc.close()
            return None, report

        report.pages_processed = doc.page_count
        audit.total_pages = doc.page_count
        audit.pages_processed = doc.page_count

        historia = HistoriaLaboral(cedula_enmascarada="ANON-XXXXX")
        records: list[CotizacionRecord] = []
        resumen_records: list[ResumenEmpleadorRecord] = []
        total_text = ""
        total_non_empty_pages = 0
        current_section = "GENERAL"

        for page_idx in range(doc.page_count):
            page = doc[page_idx]
            page_text = page.get_text("text").strip()
            method = "TEXTO_DIRECTO"

            # Check if page is empty or scanned without text layer
            if not page_text:
                # Attempt local OCR via PyMuPDF if available
                try:
                    if hasattr(page, "get_textpage_ocr"):
                        ocr_tp = page.get_textpage_ocr(language="spa")
                        page_text = page.get_text("text", textpage=ocr_tp).strip()
                        if page_text:
                            method = "OCR_LOCAL"
                except (RuntimeError, AttributeError, ValueError, OSError):
                    pass

            if page_text:
                total_non_empty_pages += 1
                total_text += page_text + "\n"

            # Extract blocks with coordinates for full spatial traceability
            blocks = page.get_text("blocks")
            # Map block coordinates to lines if possible
            block_coords_map: dict[str, list[float]] = {}
            for b in blocks:
                b_text = cls.sanitize_text(str(b[4]))
                if b_text:
                    block_coords_map[b_text[:30]] = [
                        float(b[0]),
                        float(b[1]),
                        float(b[2]),
                        float(b[3]),
                    ]

            lines = [
                cls.sanitize_text(ln) for ln in page_text.splitlines() if ln.strip()
            ]
            uninterpreted_lines: list[str] = []
            page_fragments = len(lines)
            page_fragment_records: list[dict[str, Any]] = []

            for row_idx, line in enumerate(lines):
                frag_id = f"p{page_idx + 1}_f{row_idx + 1}"
                coords = block_coords_map.get(line[:30])

                # Section transitions
                if re.search(r"INFORMACI[OÓ]N\s+DEL\s+AFILIADO", line, re.IGNORECASE):
                    current_section = "INFORMACION_AFILIADO"
                elif re.search(
                    r"RESUMEN\s+DE\s+SEMANAS\s+COTIZADAS\s+POR\s+EMPLEADOR",
                    line,
                    re.IGNORECASE,
                ):
                    current_section = "RESUMEN_EMPLEADORES"
                elif re.search(
                    r"DETALLE\s+DE\s+(?:PERIODOS|COTIZACIONES|PAGOS)",
                    line,
                    re.IGNORECASE,
                ):
                    current_section = "DETALLE_COTIZACIONES"

                # Check and skip column headers and page continuation markers
                if re.search(
                    r"\[1\]Identificaci[oó]n|Nombre\s+o\s+Raz[oó]n\s+Social|Periodo\s+Inicio.*Periodo\s+Fin|IBC\s*\(COP\)",
                    line,
                    re.IGNORECASE,
                ):
                    page_fragment_records.append(
                        {
                            "fragment_id": frag_id,
                            "page_number": page_idx + 1,
                            "order": row_idx + 1,
                            "raw_text": line,
                            "coordinates": coords,
                            "status": "HEADER",
                            "explanation": "Encabezado de columna de tabla",
                        }
                    )
                    continue

                if re.search(
                    r"RESUMEN\s+DE\s+SEMANAS.*CONTINUACI[OÓ]N|P[aá]gina\s+\d+\s+de\s+\d+",
                    line,
                    re.IGNORECASE,
                ):
                    page_fragment_records.append(
                        {
                            "fragment_id": frag_id,
                            "page_number": page_idx + 1,
                            "order": row_idx + 1,
                            "raw_text": line,
                            "coordinates": coords,
                            "status": "HEADER",
                            "explanation": "Encabezado de página o continuación",
                        }
                    )
                    continue

                # Search for start and end dates
                date_matches = list(cls.DATE_PATTERN.finditer(line))
                if len(date_matches) >= 2:
                    m1, m2 = date_matches[0], date_matches[1]
                    p_start = cls.parse_colombian_date(m1.group(0))
                    p_end = cls.parse_colombian_date(m2.group(0))

                    if p_start and p_end:
                        prefix = line[: m1.start()].strip()
                        suffix = line[m2.end() :].strip()

                        # Check if row belongs to Summary Table
                        money_in_suffix = cls.MONEY_TOKEN_PATTERN.search(suffix)
                        decimal_tokens = re.findall(r"\b\d{1,4}[.,]\d{2}\b", suffix)

                        if (
                            current_section == "RESUMEN_EMPLEADORES"
                            or len(decimal_tokens) >= 2
                        ):
                            # Parse summary row
                            nit = ""
                            nombre = prefix
                            m_nit = re.match(r"^(\d{6,12})\s+(.+)$", prefix)
                            if m_nit:
                                nit = m_nit.group(1)
                                nombre = m_nit.group(2).strip()
                            if not nombre:
                                nombre = "EMPLEADOR REPORTADO"

                            ultimo_salario = Decimal(0)
                            if money_in_suffix:
                                ultimo_salario = cls.parse_colombian_decimal(
                                    money_in_suffix.group(1)
                                )

                            sem_val = (
                                cls.parse_colombian_decimal(decimal_tokens[0])
                                if len(decimal_tokens) > 0
                                else Decimal(0)
                            )
                            lic_val = (
                                cls.parse_colombian_decimal(decimal_tokens[1])
                                if len(decimal_tokens) > 1
                                else Decimal(0)
                            )
                            sim_val = (
                                cls.parse_colombian_decimal(decimal_tokens[2])
                                if len(decimal_tokens) > 2
                                else Decimal(0)
                            )
                            tot_val = (
                                cls.parse_colombian_decimal(decimal_tokens[3])
                                if len(decimal_tokens) > 3
                                else sem_val
                            )

                            summary_rec = ResumenEmpleadorRecord(
                                nit=nit,
                                nombre_aportante=nombre,
                                periodo_inicio=p_start,
                                periodo_fin=p_end,
                                ultimo_salario=ultimo_salario,
                                semanas=sem_val,
                                licencias=lic_val,
                                simultaneidad=sim_val,
                                total_semanas=tot_val,
                                pagina=page_idx + 1,
                                fila=row_idx + 1,
                                source_fragment_ids=(frag_id,),
                            )
                            resumen_records.append(summary_rec)
                            page_fragment_records.append(
                                {
                                    "fragment_id": frag_id,
                                    "page_number": page_idx + 1,
                                    "order": row_idx + 1,
                                    "raw_text": line,
                                    "coordinates": coords,
                                    "status": "INTERPRETADO",
                                    "explanation": f"Fila resumen empleador: {nombre} ({tot_val} sem)",
                                }
                            )
                            audit.detected_fields.append(
                                DataFieldAudit(
                                    field_name=f"resumen_{summary_rec.periodo_inicio.isoformat()}",
                                    raw_text=line,
                                    parsed_value=f"Aportante={nombre}, Semanas={tot_val}, UltimoSalario={ultimo_salario}",
                                    unit="resumen",
                                    provenance="PDF",
                                    validation_status=FieldExtractionStatus.EXTRAIDO_PDF.value,
                                    explanation="Fila de resumen por empleador extraída",
                                    source_fragment_ids=[frag_id],
                                )
                            )
                        else:
                            # Parse detailed monthly contribution row
                            remainder = (
                                line[: m1.start()]
                                + " "
                                + line[m1.end() : m2.start()]
                                + " "
                                + line[m2.end() :]
                            )
                            remainder = remainder.strip()

                            # Extract money token (IBC)
                            money_match = cls.MONEY_TOKEN_PATTERN.search(remainder)
                            ibc_val = Decimal(0)
                            if money_match:
                                ibc_val = cls.parse_colombian_decimal(
                                    money_match.group(1)
                                )
                                remainder = (
                                    remainder[: money_match.start()]
                                    + " "
                                    + remainder[money_match.end() :]
                                )
                                remainder = remainder.strip()
                            else:
                                report.warnings.append(
                                    f"Fila {row_idx + 1}: IBC no detectado con certeza (IBC_AMBIGUO)."
                                )

                            # Extract days token (1 to 31)
                            days_match = cls.DAYS_PATTERN.search(remainder)
                            days_val = 0
                            dias_pendientes = False

                            if days_match:
                                days_val = int(days_match.group(1))
                                remainder = (
                                    remainder[: days_match.start()]
                                    + " "
                                    + remainder[days_match.end() :]
                                )
                                remainder = remainder.strip()
                            else:
                                # CRITICAL FIX (Finding H): Do NOT invent days_val = span_days!
                                days_val = 0
                                dias_pendientes = True
                                report.warnings.append(
                                    f"Fila {row_idx + 1}: Días cotizados ausentes en el documento (COBERTURA_PARCIAL_INCIERTA). Requiere validación manual."
                                )
                                audit.documentary_discrepancies.append(
                                    f"Fila {row_idx + 1} ({p_start.isoformat()} a {p_end.isoformat()}): Días cotizados ausentes en el documento."
                                )

                            # Clean employer name
                            employer = (
                                remainder.replace("$", "").replace("COP", "").strip()
                            )
                            employer = re.sub(r"\s+", " ", employer)
                            if not employer:
                                employer = "EMPLEADOR REPORTADO"

                            rec = CotizacionRecord(
                                periodo_inicio=p_start,
                                periodo_fin=p_end,
                                dias_reportados=days_val,
                                dias_cotizados=days_val,
                                ibc=ibc_val,
                                aportante=employer,
                                origen=ProvenanceType.PDF,
                                pagina=page_idx + 1,
                                fila=row_idx + 1,
                                dias_pendientes_validacion=dias_pendientes,
                                source_fragment_ids=(frag_id,),
                            )
                            records.append(rec)

                            # Record fragment audit
                            frag_status = (
                                "AMBIGUO" if dias_pendientes else "INTERPRETADO"
                            )
                            frag_expl = (
                                "Fila interpretada con días pendientes de validación"
                                if dias_pendientes
                                else "Fila de cotización válida extraída"
                            )
                            page_fragment_records.append(
                                {
                                    "fragment_id": frag_id,
                                    "page_number": page_idx + 1,
                                    "order": row_idx + 1,
                                    "raw_text": line,
                                    "coordinates": coords,
                                    "status": frag_status,
                                    "explanation": frag_expl,
                                }
                            )

                            # Record field audit
                            audit.detected_fields.append(
                                DataFieldAudit(
                                    field_name=f"cotizacion_{rec.periodo_inicio.isoformat()}",
                                    raw_text=line,
                                    parsed_value=f"IBC={ibc_val}, Días={days_val}",
                                    unit="registro",
                                    provenance="PDF",
                                    validation_status="PENDIENTE_REVISION"
                                    if dias_pendientes
                                    else "VERIFICADO",
                                    explanation=frag_expl,
                                    source_fragment_ids=[frag_id],
                                )
                            )
                    else:
                        uninterpreted_lines.append(line)
                        page_fragment_records.append(
                            {
                                "fragment_id": frag_id,
                                "page_number": page_idx + 1,
                                "order": row_idx + 1,
                                "raw_text": line,
                                "coordinates": coords,
                                "status": "RECHAZADO",
                                "explanation": "Fechas inválidas",
                            }
                        )
                else:
                    uninterpreted_lines.append(line)
                    page_fragment_records.append(
                        {
                            "fragment_id": frag_id,
                            "page_number": page_idx + 1,
                            "order": row_idx + 1,
                            "raw_text": line,
                            "coordinates": coords,
                            "status": "NO_COTIZACION",
                            "explanation": "No contiene estructura de cotización",
                        }
                    )

            # Preserve uninterpreted lines without silent truncation (Issue A)
            audit.pages_audit.append(
                PageExtractionAudit(
                    page_number=page_idx + 1,
                    method=method,
                    text_length=len(page_text),
                    fragments_detected=page_fragments,
                    raw_page_text=page_text,
                    fragments=page_fragment_records,
                    uninterpreted_lines=uninterpreted_lines,
                )
            )

        # Detect completely empty or scanned PDF without text
        if total_non_empty_pages == 0 or len(total_text.strip()) == 0:
            report.error_message = "PDF_VACIO: El documento PDF no contiene texto digital ni se pudieron extraer capas legibles."
            report.warnings.append(
                "Documento escaneado sin texto o completamente vacío (PDF_SIN_TEXTO_OCR_LOCAL)."
            )
            audit.extraction_status = "INCOMPLETA"
            AuditService.log_technical(
                exec_id,
                AuditStep.EXTRACCION_PDF,
                "ColpensionesPDFReader",
                0.0,
                AuditSeverity.ADVERTENCIA,
                EventCode.PDF_VACIO,
                "BLOQUEADO",
                "PDF sin texto",
                "Solicitar versión digitalizada con texto",
            )
            doc.close()
            return None, report

        # Extract metadata from sanitized total text
        # 0. Nombre del Afiliado y Cédula
        m_name = re.search(
            r"(?:Nombre\s+(?:del\s+)?Afiliado|Nombre)[:\s]*([^\n\r]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_name:
            historia.nombre_enmascarado = cls.sanitize_text(m_name.group(1)).strip()
            audit.detected_fields.append(
                DataFieldAudit(
                    "nombre_enmascarado",
                    m_name.group(0),
                    historia.nombre_enmascarado,
                    "texto",
                    "PDF",
                    FieldExtractionStatus.EXTRAIDO_PDF.value,
                    "Extraído de los datos del afiliado",
                )
            )

        m_cedula = re.search(
            r"(?:N[uú]mero\s+de\s+Documento|C[eé]dula(?:\s+de\s+Ciudadan[ií]a)?|Identificaci[oó]n)[:\s]*([0-9Xx*.-]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_cedula:
            historia.cedula_enmascarada = m_cedula.group(1).strip()
            audit.detected_fields.append(
                DataFieldAudit(
                    "cedula_enmascarada",
                    m_cedula.group(0),
                    historia.cedula_enmascarada,
                    "documento",
                    "PDF",
                    FieldExtractionStatus.EXTRAIDO_PDF.value,
                    "Extraído del número de identificación",
                )
            )

        # 1. Fecha de Nacimiento (supports same line or adjacent lines)
        m_birth = re.search(
            r"Fecha\s+de\s+Nacimiento[:\s]*([0-9/.-]+|[A-Za-z0-9\s]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_birth:
            historia.fecha_nacimiento = cls.parse_colombian_date(m_birth.group(1))
            if historia.fecha_nacimiento:
                audit.detected_fields.append(
                    DataFieldAudit(
                        "fecha_nacimiento",
                        m_birth.group(0),
                        str(historia.fecha_nacimiento),
                        "fecha",
                        "PDF",
                        FieldExtractionStatus.EXTRAIDO_PDF.value,
                        "Extraído del bloque de información del afiliado",
                        ["p1_f1"],
                    )
                )

        # 2. Fecha de Afiliación Colpensiones
        m_af = re.search(
            r"Fecha\s+(?:de\s+)?Afiliaci[oó]n[:\s]*([0-9/.-]+|[A-Za-z0-9\s]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_af:
            historia.fecha_afiliacion_colpensiones = cls.parse_colombian_date(
                m_af.group(1)
            )
            if historia.fecha_afiliacion_colpensiones:
                audit.detected_fields.append(
                    DataFieldAudit(
                        "fecha_afiliacion_colpensiones",
                        m_af.group(0),
                        str(historia.fecha_afiliacion_colpensiones),
                        "fecha",
                        "PDF",
                        FieldExtractionStatus.EXTRAIDO_PDF.value,
                        "Extraído de la fecha de afiliación informada",
                        ["p1_f1"],
                    )
                )

        # 3. Estado de Afiliación
        m_est = re.search(
            r"Estado\s+(?:de\s+)?Afiliaci[oó]n[:\s]*([A-Za-z\s]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_est:
            val_est = m_est.group(1).upper()
            if "ACTIVO" in val_est:
                historia.estado_afiliacion = AffiliationStatus.ACTIVO
            elif "INACTIVO" in val_est:
                historia.estado_afiliacion = AffiliationStatus.INACTIVO
            elif "PENSIONADO" in val_est:
                historia.estado_afiliacion = AffiliationStatus.PENSIONADO
            else:
                historia.estado_afiliacion = AffiliationStatus.DESCONOCIDO
            audit.detected_fields.append(
                DataFieldAudit(
                    "estado_afiliacion",
                    m_est.group(0),
                    historia.estado_afiliacion.value,
                    "estado",
                    "PDF",
                    FieldExtractionStatus.EXTRAIDO_PDF.value,
                    "Extraído del estado de afiliación reportado",
                )
            )
        else:
            historia.estado_afiliacion = AffiliationStatus.DESCONOCIDO

        # 4. Sexo / Categoría Pensional (Strictly: None if not present!)
        m_sex = re.search(
            r"\b(?:Sexo|G[eé]nero)[:\s]+(FEMENINO|MASCULINO|MUJER|HOMBRE|F|M)\b",
            total_text,
            re.IGNORECASE,
        )
        if m_sex:
            val_s = m_sex.group(1).upper()
            if val_s in ("FEMENINO", "MUJER", "F"):
                historia.sexo = SexCategory.FEMENINO
            elif val_s in ("MASCULINO", "HOMBRE", "M"):
                historia.sexo = SexCategory.MASCULINO
            else:
                historia.sexo = None

            if historia.sexo:
                audit.detected_fields.append(
                    DataFieldAudit(
                        "sexo",
                        m_sex.group(0),
                        historia.sexo.value,
                        "categoria",
                        "PDF",
                        FieldExtractionStatus.EXTRAIDO_PDF.value,
                    )
                )
        else:
            historia.sexo = None
            audit.detected_fields.append(
                DataFieldAudit(
                    "sexo",
                    "",
                    None,
                    "categoria",
                    "PDF",
                    FieldExtractionStatus.NO_ENCONTRADO.value,
                    "Categoría pensional ausente en el documento. Requiere selección del usuario.",
                )
            )

        # 5. Fecha de Actualización del Reporte (e.g. ACTUALIZADO A: 30 agosto 2025)
        m_act = re.search(
            r"(?:ACTUALIZADO\s+A|FECHA\s+DE\s+ACTUALIZACI[OÓ]N)[:\s]*([^\n\r]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_act:
            historia.fecha_actualizacion_reporte = cls.parse_colombian_date(
                m_act.group(1)
            )
            if historia.fecha_actualizacion_reporte:
                audit.detected_fields.append(
                    DataFieldAudit(
                        "fecha_actualizacion_reporte",
                        m_act.group(0),
                        str(historia.fecha_actualizacion_reporte),
                        "fecha",
                        "PDF",
                        FieldExtractionStatus.EXTRAIDO_PDF.value,
                        "Fecha de actualización documental del reporte",
                    )
                )

        # 6. Fecha de Expedición del Reporte (separated from Actualizado a)
        m_exp = re.search(
            r"(?:FECHA\s+DE\s+EXPEDICI[OÓ]N|EXPEDIDO\s+EL)[:\s]*([^\n\r]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_exp:
            historia.fecha_expedicion_reporte = cls.parse_colombian_date(m_exp.group(1))
            if historia.fecha_expedicion_reporte:
                audit.detected_fields.append(
                    DataFieldAudit(
                        "fecha_expedicion_reporte",
                        m_exp.group(0),
                        str(historia.fecha_expedicion_reporte),
                        "fecha",
                        "PDF",
                        FieldExtractionStatus.EXTRAIDO_PDF.value,
                        "Fecha de expedición formal del certificado",
                    )
                )

        # Fallback when only one of the dates is present in document
        if (
            historia.fecha_actualizacion_reporte is None
            and historia.fecha_expedicion_reporte is not None
        ):
            historia.fecha_actualizacion_reporte = historia.fecha_expedicion_reporte
        elif (
            historia.fecha_expedicion_reporte is None
            and historia.fecha_actualizacion_reporte is not None
        ):
            historia.fecha_expedicion_reporte = historia.fecha_actualizacion_reporte

        # 7. Total Semanas Resumen Colpensiones
        m_weeks = re.search(
            r"(?:TOTAL\s+GENERAL\s+DE\s+SEMANAS|TOTAL\s+DE\s+SEMANAS|TOTAL\s+SEMANAS|Semanas\s+Cotizadas)[:\s]+([0-9.,]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_weeks:
            historia.semanas_resumen_colpensiones = cls.parse_colombian_decimal(
                m_weeks.group(1)
            )
            audit.detected_fields.append(
                DataFieldAudit(
                    "semanas_resumen_colpensiones",
                    m_weeks.group(0),
                    float(historia.semanas_resumen_colpensiones),
                    "semanas",
                    "PDF",
                    FieldExtractionStatus.EXTRAIDO_PDF.value,
                )
            )
        elif resumen_records:
            historia.semanas_resumen_colpensiones = sum(
                (r.total_semanas for r in resumen_records), Decimal(0)
            )
            audit.detected_fields.append(
                DataFieldAudit(
                    "semanas_resumen_colpensiones",
                    "Suma total de filas de resumen",
                    float(historia.semanas_resumen_colpensiones),
                    "semanas",
                    "PDF",
                    FieldExtractionStatus.EXTRAIDO_PDF.value,
                )
            )

        # 8. Semanas de Alto Riesgo (Strictly: None if not present!)
        m_hr = re.search(
            r"(?:Semanas\s+de\s+Alto\s+Riesgo(?:\s*\([^)]*\))?|Alto\s+Riesgo)[:\s]+([0-9.,]+)",
            total_text,
            re.IGNORECASE,
        )
        if m_hr:
            historia.semanas_alto_riesgo = cls.parse_colombian_decimal(m_hr.group(1))
            if historia.semanas_alto_riesgo > Decimal(0):
                historia.es_caso_especial = True
                historia.detalle_caso_especial = f"Registra {historia.semanas_alto_riesgo} semanas de alto riesgo (Decreto 2090 de 2003)."
            audit.detected_fields.append(
                DataFieldAudit(
                    "semanas_alto_riesgo",
                    m_hr.group(0),
                    float(historia.semanas_alto_riesgo),
                    "semanas",
                    "PDF",
                    FieldExtractionStatus.EXTRAIDO_PDF.value,
                )
            )
        else:
            historia.semanas_alto_riesgo = None
            audit.detected_fields.append(
                DataFieldAudit(
                    "semanas_alto_riesgo",
                    "",
                    None,
                    "semanas",
                    "PDF",
                    FieldExtractionStatus.NO_ENCONTRADO.value,
                    "Semanas de alto riesgo no mencionadas expresamente en el reporte.",
                )
            )

        # 9. Determine First and Last Period
        all_starts = [r.periodo_inicio for r in records] + [
            r.periodo_inicio for r in resumen_records
        ]
        all_ends = [r.periodo_fin for r in records] + [
            r.periodo_fin for r in resumen_records
        ]

        if all_starts:
            historia.fecha_primera_cotizacion = min(all_starts)
        if all_ends:
            historia.ultimo_periodo_cotizado = max(all_ends)

        # 10. Assign collections to historia
        historia.registros = records
        historia.resumen_empleadores = resumen_records
        report.records_extracted = len(records)

        # 11. Add warning if only summary was extracted
        if historia.resumen_empleadores and not historia.registros:
            report.warnings.append(
                f"Se detectó la tabla 'RESUMEN DE SEMANAS COTIZADAS POR EMPLEADOR' con {len(historia.resumen_empleadores)} períodos "
                f"({historia.semanas_resumen_colpensiones} semanas reconocidas). El documento no contiene la tabla de detalle mensual de cotizaciones "
                "(IBC histórico); para proyectar la mesada pensional se requerirá ingresar el IBC estimado o cargar un reporte detallado."
            )

        report.success = True
        audit.extraction_status = (
            "COMPLETA" if (records or resumen_records) else "ADVERTENCIA"
        )

        AuditService.log_technical(
            exec_id,
            AuditStep.EXTRACCION_PDF,
            "ColpensionesPDFReader",
            0.0,
            AuditSeverity.INFO,
            EventCode.PDF_CARGADO,
            "COMPLETADO",
            f"Extraídos {len(records)} registros de detalle y {len(resumen_records)} de resumen en {doc.page_count} páginas",
            "Continuar a validación documental",
        )

        doc.close()
        return historia, report
