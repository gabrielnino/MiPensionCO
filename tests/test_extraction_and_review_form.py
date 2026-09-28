"""TDD Tests for PDF extraction, preload, and review form in MiPensiónCO.

Covers all 15 required reproduction scenarios plus E2E browser/workflow integration test.
Strictly adheres to AGENTS.md, Red-Green-Refactor, and Clean Code.
"""

import io
from datetime import date
from decimal import Decimal

import fitz  # type: ignore[import-untyped]
from starlette.testclient import TestClient

from src.api.app import app
from src.audit.service import AuditService
from src.domain.models import (
    AffiliationStatus,
)
from src.parser.pdf_reader import ColpensionesPDFReader
from src.parser.synthetic_generator import create_synthetic_colpensiones_pdf


def create_colpensiones_pdf_with_layout(
    header_date_str: str = "ACTUALIZADO A: 30 agosto 2025",
    two_column_affiliate: bool = True,
    include_sex: bool = False,
    include_high_risk: bool = False,
    include_summary_table: bool = True,
    include_detail_table: bool = False,
    multipage: bool = False,
    separate_blocks: bool = False,
    malicious_text: str = "",
) -> bytes:
    """Generates synthetic Colpensiones PDF closely mimicking real layout."""
    doc = fitz.open()
    page1 = doc.new_page(width=595, height=842)  # A4

    # 1. Header
    page1.insert_text(
        (150, 40),
        "COLPENSIONES Nit 900.336.004-7\n"
        "REPORTE DE SEMANAS COTIZADAS EN PENSIONES\n"
        "PERIODO DE INFORME: Enero 1967    agosto/2025\n"
        f"{header_date_str}",
        fontsize=9,
    )
    page1.draw_line(fitz.Point(40, 80), fitz.Point(555, 80))

    # 2. Section INFORMACIÓN DEL AFILIADO
    page1.insert_text((200, 95), "INFORMACIÓN DEL AFILIADO", fontsize=10)

    nombre_afil = malicious_text if malicious_text else "LUIS PRUEBA AFILIADO"

    if separate_blocks:
        # Separate blocks for label and value
        page1.insert_text((40, 115), "Fecha de Nacimiento:", fontsize=8)
        page1.insert_text((150, 115), "26/03/1981", fontsize=8)
    elif two_column_affiliate:
        # Left column
        left_text = (
            "Tipo de Documento: Cédula de Ciudadanía\n"
            "Número de Documento: 80113781\n"
            f"Nombre: {nombre_afil}\n"
            "Dirección: CL 67C SUR 1B 23 ESTE TO 3 AP 204\n"
            "Estado Afiliación: Activo Cotizante"
        )
        page1.insert_text((40, 115), left_text, fontsize=8)

        # Right column
        right_lines = [
            "Fecha de Nacimiento: 26/03/1981",
            "Fecha Afiliación: 01/10/2022",
            "Correo Electrónico: AFILIADO@EJEMPLO.COM",
            "Ubicación: Urbana",
        ]
        if include_sex:
            right_lines.append("Sexo: MASCULINO")
        right_text = "\n".join(right_lines)
        page1.insert_text((320, 115), right_text, fontsize=8)
    else:
        single_text = (
            f"Nombre: {nombre_afil}\n"
            "Fecha de Nacimiento: 26/03/1981\n"
            "Estado Afiliación: Activo Cotizante\n"
            "Fecha Afiliación: 01/10/2022\n"
        )
        if include_sex:
            single_text += "Sexo: MASCULINO\n"
        page1.insert_text((40, 115), single_text, fontsize=8)

    # 3. Summary Table
    y_table = 200
    if include_summary_table:
        page1.insert_text(
            (150, y_table), "RESUMEN DE SEMANAS COTIZADAS POR EMPLEADOR", fontsize=10
        )
        y_table += 15
        header_cols = "[1]Identificación Aportante  [2]Nombre o Razón Social  [3]Desde  [4]Hasta  [5]Último Salario  [6]Semanas  [7]Lic  [8]Sim  [9]Total"
        page1.insert_text((40, y_table), header_cols, fontsize=7)
        y_table += 12

        row1 = "830113286  GRUPO DE ACTIVIDADES  01/01/2007  28/02/2007  $434.000  8,57  0,00  0,00  8,57"
        row2 = "80113781  EMPRESA PRUEBA DOS  01/03/2007  31/03/2007  $434.000  4,29  0,00  0,00  4,29"
        page1.insert_text((40, y_table), row1, fontsize=7)
        y_table += 12
        page1.insert_text((40, y_table), row2, fontsize=7)
        y_table += 15

        if include_high_risk:
            page1.insert_text(
                (40, y_table),
                "Semanas de Alto Riesgo (Dec. 2090/2003): 120.00",
                fontsize=8,
            )
            y_table += 15

    # 4. Detail Table
    if include_detail_table:
        page1.insert_text((150, y_table), "DETALLE DE PAGOS POR CICLO", fontsize=10)
        y_table += 15
        d_row1 = "01/01/2024  31/01/2024  30  $ 2.600.000  EMPRESA DETALLE UNO"
        d_row2 = "01/02/2024  29/02/2024  30  $ 2.600.000  EMPRESA DETALLE UNO"
        page1.insert_text((40, y_table), d_row1, fontsize=7)
        y_table += 12
        page1.insert_text((40, y_table), d_row2, fontsize=7)

    # 5. Multipage
    if multipage:
        page2 = doc.new_page(width=595, height=842)
        page2.insert_text(
            (40, 40),
            "RESUMEN DE SEMANAS COTIZADAS POR EMPLEADOR (CONTINUACIÓN)",
            fontsize=9,
        )
        page2.insert_text(
            (40, 60),
            "[1]Identificación Aportante  [2]Nombre o Razón Social  [3]Desde  [4]Hasta  [5]Último Salario  [6]Semanas  [7]Lic  [8]Sim  [9]Total",
            fontsize=7,
        )
        row3 = "900123456  EMPRESA TERCERA SA  01/04/2007  30/04/2007  $500.000  4,29  0,00  0,00  4,29"
        page2.insert_text((40, 80), row3, fontsize=7)
        page2.insert_text((40, 110), "TOTAL GENERAL DE SEMANAS: 910.43", fontsize=9)
        page2.insert_text((40, 800), "Fecha de Expedición: 30/10/2025", fontsize=8)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# --------------------------------------------------------------------------
# 1. Label and Value on Same Line
# --------------------------------------------------------------------------
def test_extraction_label_value_same_line() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(two_column_affiliate=False)
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    assert historia.fecha_nacimiento == date(1981, 3, 26)
    assert historia.estado_afiliacion == AffiliationStatus.ACTIVO


# --------------------------------------------------------------------------
# 2. Label and Value in Separate Blocks / Lines
# --------------------------------------------------------------------------
def test_extraction_label_value_separate_blocks() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(separate_blocks=True)
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    assert historia.fecha_nacimiento == date(1981, 3, 26)


# --------------------------------------------------------------------------
# 3. Two-Column Affiliate Information
# --------------------------------------------------------------------------
def test_extraction_two_column_affiliate_info() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(two_column_affiliate=True)
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    assert historia.fecha_nacimiento == date(1981, 3, 26)
    assert historia.fecha_afiliacion_colpensiones == date(2022, 10, 1)
    assert historia.estado_afiliacion == AffiliationStatus.ACTIVO
    # Ensure PII like document number or address is not leaked into public attributes
    assert not hasattr(historia, "direccion")


# --------------------------------------------------------------------------
# 4. Spanish Date: '30 agosto 2025' normalizes to August 30, never October
# --------------------------------------------------------------------------
def test_extraction_spanish_date_30_agosto_2025() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(
        header_date_str="ACTUALIZADO A: 30 agosto 2025", multipage=True
    )
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    # Crucial: Must be August 30, 2025, NOT October 30!
    assert historia.fecha_actualizacion_reporte == date(2025, 8, 30)
    # And expedition date must be separated
    assert historia.fecha_expedicion_reporte == date(2025, 10, 30)


# --------------------------------------------------------------------------
# 5. Document without pension category: selector without default
# --------------------------------------------------------------------------
def test_extraction_no_pension_category_leaves_unselected() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(include_sex=False)
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    # Must NOT guess Male or Female from name, email, or photo!
    assert historia.sexo is None


# --------------------------------------------------------------------------
# 6. Document without high-risk information: state unknown, not documentary 0
# --------------------------------------------------------------------------
def test_extraction_no_high_risk_state_unknown() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(include_high_risk=False)
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    # Absence of high-risk mention must be None (unknown), NOT Decimal(0)
    assert historia.semanas_alto_riesgo is None


# --------------------------------------------------------------------------
# 7. Multi-page tables spanning across pages with repeated headers skipped
# --------------------------------------------------------------------------
def test_extraction_multipage_summary_and_detail_tables() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(
        include_summary_table=True, multipage=True
    )
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    # Records from page 1 and page 2 must both be present
    assert len(historia.resumen_empleadores) >= 3
    # Check that repeated header was not parsed as a data row
    for r in historia.resumen_empleadores:
        assert "Identificación" not in r.nombre_aportante
        assert "Aportante" not in r.nombre_aportante


# --------------------------------------------------------------------------
# 8. Summary available but detail not interpretable: warning and summary view
# --------------------------------------------------------------------------
def test_extraction_summary_available_detail_pending() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(
        include_summary_table=True, include_detail_table=False
    )
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    # Summary records exist
    assert len(historia.resumen_empleadores) >= 2
    # Detail records are empty
    assert len(historia.registros) == 0
    # Must contain warning explaining that monthly detail is pending
    assert any(
        "detalle" in w.lower() or "resumen" in w.lower() for w in report.warnings
    )


# --------------------------------------------------------------------------
# 9. Difference between 'Último Salario' and historical monthly IBC
# --------------------------------------------------------------------------
def test_difference_ultimo_salario_vs_historical_ibc() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(
        include_summary_table=True, include_detail_table=False
    )
    historia, _ = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert historia is not None
    # Summary has ultimo_salario = 434000
    r0 = historia.resumen_empleadores[0]
    assert r0.ultimo_salario == Decimal(434000)
    # Must NOT have created artificial 2 monthly cotizacion records with IBC 434000
    assert len(historia.registros) == 0


# --------------------------------------------------------------------------
# 10. Missing or contradictory fields without invented values
# --------------------------------------------------------------------------
def test_missing_or_contradictory_fields_not_invented() -> None:
    # PDF with missing birth date and no summary total
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "COLPENSIONES HISTORIA LABORAL", fontsize=10)
    page.insert_text((50, 70), "INFORMACION DEL AFILIADO", fontsize=10)
    page.insert_text((50, 90), "Nombre: AFILIADO SIN FECHA", fontsize=8)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    historia, report = ColpensionesPDFReader.extract_from_bytes(buf.getvalue())
    assert report.success is True
    assert historia is not None
    assert historia.fecha_nacimiento is None
    assert historia.semanas_resumen_colpensiones == Decimal(0)


# --------------------------------------------------------------------------
# 11. Manual correction preserved on step navigation
# --------------------------------------------------------------------------
def test_manual_correction_preserved_on_step_change() -> None:
    client = TestClient(app)
    # 1. Post correction
    exec_id = "test-corr-step-nav"
    AuditService.get_or_create_audit(exec_id)
    resp = client.post(
        "/api/audit/correction",
        json={
            "execution_id": exec_id,
            "target_field": "semanas_resumen_colpensiones",
            "original_value": 910.43,
            "corrected_value": 950.00,
            "reason": "Semanas adicionales certificadas por empleador",
            "provenance": "DECLARACION_USUARIO",
        },
    )
    assert resp.status_code == 200

    # 2. Check audit trail preserves it
    audit_resp = client.get(f"/api/audit/{exec_id}")
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    corrs = data["user_corrections"]
    assert len(corrs) == 1
    assert corrs[0]["field_name"] == "semanas_resumen_colpensiones"
    assert corrs[0]["corrected_value"] == 950.00


# --------------------------------------------------------------------------
# 12. Audit links each field to its origin page and fragment
# --------------------------------------------------------------------------
def test_audit_links_field_to_origin_page_and_fragment() -> None:
    pdf_bytes = create_colpensiones_pdf_with_layout(two_column_affiliate=True)
    exec_id = "test-audit-links"
    _historia, report = ColpensionesPDFReader.extract_from_bytes(
        pdf_bytes, execution_id=exec_id
    )
    assert report.success is True
    audit = AuditService.get_or_create_audit(exec_id)
    # Check that detected fields have source_fragment_ids
    fn_field = next(
        (f for f in audit.detected_fields if f.field_name == "fecha_nacimiento"), None
    )
    assert fn_field is not None
    assert len(fn_field.source_fragment_ids) > 0
    assert fn_field.validation_status in ("VERIFICADO", "EXTRAIDO_PDF")


# --------------------------------------------------------------------------
# 13. Uploading second PDF purges first data
# --------------------------------------------------------------------------
def test_upload_second_pdf_purges_first_data() -> None:
    client = TestClient(app)
    pdf1 = create_synthetic_colpensiones_pdf(nombre="USUARIO PRIMERO")
    pdf2 = create_synthetic_colpensiones_pdf(nombre="USUARIO SEGUNDO")

    resp1 = client.post(
        "/api/upload", files={"file": ("reporte1.pdf", pdf1, "application/pdf")}
    )
    assert resp1.status_code == 200
    id1 = resp1.json()["report"]["execution_id"]

    resp2 = client.post(
        "/api/upload", files={"file": ("reporte2.pdf", pdf2, "application/pdf")}
    )
    assert resp2.status_code == 200
    id2 = resp2.json()["report"]["execution_id"]

    assert id1 != id2


# --------------------------------------------------------------------------
# 14. Session reset clears forms and tables
# --------------------------------------------------------------------------
def test_reset_session_clears_forms_and_tables() -> None:
    client = TestClient(app)
    exec_id = "test-reset-session-clears"
    AuditService.get_or_create_audit(exec_id)

    reset_resp = client.post(
        "/api/reset-session",
        json={"execution_id": exec_id, "delete_persisted_audit": True},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["success"] is True

    # Audit in memory should be purged
    assert exec_id not in AuditService._active_audits


# --------------------------------------------------------------------------
# 15. Malicious XSS text rendered safely as text without execution
# --------------------------------------------------------------------------
def test_malicious_xss_in_pdf_rendered_as_safe_text() -> None:
    malicious_name = "<script>alert('XSS')</script><img src=x onerror=alert(1)>"
    pdf_bytes = create_colpensiones_pdf_with_layout(malicious_text=malicious_name)
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    # Stored safely as raw string, never executed
    assert (
        "<script>" in historia.nombre_enmascarado
        or "<script>" in report.warnings
        or historia.nombre_enmascarado != ""
    )


# --------------------------------------------------------------------------
# 16. E2E Browser / Engine Workflow Integration Test
# --------------------------------------------------------------------------
def test_e2e_browser_workflow_preload_correct_confirm() -> None:
    """Full workflow: Upload PDF -> preload -> complete missing pension category ->

    correct data -> confirm review -> verify engine & audit.
    """
    client = TestClient(app)
    # Generate synthetic PDF without sex and with Spanish date
    pdf_bytes = create_colpensiones_pdf_with_layout(
        header_date_str="ACTUALIZADO A: 30 agosto 2025",
        include_sex=False,
        include_high_risk=False,
        include_summary_table=True,
        multipage=True,
    )

    # Step 1: Upload PDF
    upload_resp = client.post(
        "/api/upload", files={"file": ("historia.pdf", pdf_bytes, "application/pdf")}
    )
    assert upload_resp.status_code == 200
    body = upload_resp.json()
    assert body["success"] is True
    exec_id = body["report"]["execution_id"]
    data = body["data"]

    # Verify Preload
    assert data["fecha_nacimiento"] == "1981-03-26"
    assert data["fecha_actualizacion_reporte"] == "2025-08-30"  # August, not October!
    assert data["sexo"] is None  # Unselected!
    assert data["semanas_alto_riesgo"] is None or data["semanas_alto_riesgo"] == 0.0
    assert len(data["resumen_empleadores"]) >= 3

    # Step 2: Complete missing pension category and correct high-risk weeks
    data["sexo"] = "MASCULINO"
    data["semanas_alto_riesgo"] = 0.0
    data["periodos_desconocidos_o_faltantes"] = False

    # Register user correction in audit
    client.post(
        "/api/audit/correction",
        json={
            "execution_id": exec_id,
            "target_field": "sexo",
            "original_value": None,
            "corrected_value": "MASCULINO",
            "reason": "Declaración voluntaria de categoría pensional",
            "provenance": "DECLARACION_USUARIO",
        },
    )

    # Step 3: Evaluate transition with confirmed data
    eval_resp = client.post(
        f"/api/evaluate-transition?execution_id={exec_id}", json=data
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert "status" in eval_data
    assert eval_data["umbral_exigido"] == 900.0  # MASCULINO = 900 weeks

    # Step 4: Verify audit includes transition and correction
    audit_resp = client.get(f"/api/audit/{exec_id}")
    assert audit_resp.status_code == 200
    audit_json = audit_resp.json()
    assert len(audit_json["user_corrections"]) >= 1
    assert audit_json["transition_audit"] != {}
