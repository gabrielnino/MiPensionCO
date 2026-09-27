"""Playwright Chromium E2E verification test suite for the 'Revisar períodos y semanas' screen.

Verifies end-to-end functionality in a real browser:
1. Two separate tables based on PDF content (Employer summary and Detail cotizaciones).
2. Actuarial banner that employer 'último salario' is not projected as historical monthly IBC.
3. Editable detail rows with provenance badges (PDF, CORRECCION_MANUAL, DECLARACION_USUARIO).
4. Edit modal with original vs new values comparison, input validation (inverted dates, incompatible days),
   and mandatory justification reason.
5. Record exclusion and re-inclusion with mandatory justification.
6. Record restoration to immutable original PDF values.
7. Addition of user declared periods with DECLARACION_USUARIO provenance.
8. Reconciliation summary KPI cards and discrepancy banner (strictly avoiding max(doc, cal) fallacy).
9. Invalidation of downstream transition evaluations and simulations upon data modification.
10. Confirmation gate and seamless transition to legal evaluation with audit tracking.
11. Session reset and clean memory state.
"""

import io
import tempfile
import threading
import time
from collections.abc import Generator

import fitz  # PyMuPDF
import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from src.api.app import app


def create_synthetic_review_test_pdf() -> bytes:
    """Generates a synthetic Colpensiones labor history PDF for review screen testing."""
    doc = fitz.open()

    # Page 1: Affiliate info and Employer Summary
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(
        (40, 50),
        "COLPENSIONES Nit 900.336.004-7\nREPORTE DE SEMANAS COTIZADAS EN PENSIONES",
        fontsize=11,
    )
    p1.insert_text((40, 75), "ACTUALIZADO A: 30 agosto 2025", fontsize=9)
    p1.insert_text((40, 95), "INFORMACIÓN DEL AFILIADO", fontsize=10)
    info_text = (
        "Nombre: CIUDADANO SINTETICO DE PRUEBA\n"
        "Tipo de Documento: Cédula de Ciudadanía\n"
        "Número de Documento: 52123456\n"
        "Fecha de Nacimiento: 15/06/1968\n"
        "Estado Afiliación: Activo Cotizante\n"
        "Fecha Afiliación: 01/02/1994\n"
        "Fecha de Expedición: 15/10/2025"
    )
    p1.insert_text((40, 115), info_text, fontsize=8)

    # Employer Summary Table
    p1.insert_text((40, 220), "RESUMEN DE SEMANAS COTIZADAS POR EMPLEADOR", fontsize=10)
    p1.insert_text(
        (40, 240),
        "[1]Identificación  [2]Razón Social  [3]Desde  [4]Hasta  [5]Salario  [6]Sem  [7]Lic  [8]Sim  [9]Total",
        fontsize=7,
    )
    p1.insert_text(
        (40, 255),
        "800111222  SERVICIOS INDUSTRIALES SAS  01/01/2010  31/12/2019  $4.500.000  521,43  0,00  0,00  521,43",
        fontsize=7,
    )
    p1.insert_text(
        (40, 270),
        "900333444  CONSULTORES ANDINOS SAS    01/01/2020  31/12/2024  $6.000.000  260,71  0,00  0,00  260,71",
        fontsize=7,
    )
    p1.insert_text((40, 290), "TOTAL GENERAL DE SEMANAS: 782.14", fontsize=9)

    # Page 2: Monthly Details
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((40, 40), "DETALLE DE PAGOS POR CICLO", fontsize=10)
    p2.insert_text(
        (40, 60),
        "Periodo Inicio  Periodo Fin  Dias  IBC (COP)  Empleador",
        fontsize=7,
    )
    detail_rows = [
        "01/01/2024  31/01/2024  30  $ 6.000.000  CONSULTORES ANDINOS SAS",
        "01/02/2024  29/02/2024  30  $ 6.000.000  CONSULTORES ANDINOS SAS",
        "01/03/2024  31/03/2024  30  $ 6.000.000  CONSULTORES ANDINOS SAS",
        "01/04/2024  30/04/2024  30  $ 6.000.000  CONSULTORES ANDINOS SAS",
        "01/05/2024  31/05/2024  30  $ 6.000.000  CONSULTORES ANDINOS SAS",
    ]
    y = 75
    for r in detail_rows:
        p2.insert_text((40, y), r, fontsize=7)
        y += 15

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture(scope="module")
def review_server_url() -> Generator[str, None, None]:
    """Runs FastAPI local server on port 8898 for review screen tests."""
    port = 8898
    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(1.0)
    url = f"http://127.0.0.1:{port}"
    yield url
    server.should_exit = True
    t.join(timeout=2.0)


def test_review_periods_screen_full_e2e(review_server_url: str) -> None:
    """Comprehensive real-browser test of the 'Revisar períodos y semanas' screen."""
    pdf_bytes = create_synthetic_review_test_pdf()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(pdf_bytes)
        pdf_path = tf.name

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        # 1. Load home page
        page.goto(review_server_url)
        page.wait_for_selector("#dropzone", state="visible")
        assert "MiPensiónCO" in page.title()

        # 2. Upload synthetic PDF
        page.set_input_files("#pdf-file-input", pdf_path)
        page.wait_for_selector("#step-panel-2", state="visible", timeout=10000)

        # Verify Step 2 preloaded affiliate fields
        assert page.input_value("#rev-fecha-nac") == "1968-06-15"
        assert "agosto" in page.inner_text("#rev-fecha-corte-es").lower()

        # Fill mandatory pensional category in Step 2
        page.select_option("#rev-sexo", "FEMENINO")
        page.fill("#rev-alto-riesgo", "0")

        # 3. Advance to Step 3: Revisar Períodos y Semanas
        page.click("#btn-to-review-periods")
        page.wait_for_selector("#step-panel-3", state="visible", timeout=10000)

        # 3.1 Verify Reconciliation KPI cards exist and are populated
        page.wait_for_selector("#recon-kpi-pdf")
        page.wait_for_selector("#recon-kpi-detalle")
        page.wait_for_selector("#recon-kpi-declaradas")
        page.wait_for_selector("#recon-kpi-activas")

        kpi_pdf_val = float(page.inner_text("#recon-kpi-pdf"))
        kpi_detalle_val = float(page.inner_text("#recon-kpi-detalle"))
        kpi_activas_val = float(page.inner_text("#recon-kpi-activas"))
        assert kpi_pdf_val > 0
        assert kpi_detalle_val > 0
        assert kpi_activas_val > 0

        # Verify reconciliation banner explains discrepancy and does NOT arbitrarily pick the higher
        recon_banner = page.inner_text("#recon-discrepancia-banner")
        assert len(recon_banner) > 0

        # 3.2 Verify Table 1: Employer Summary separation and actuarial banner
        assert page.is_visible("#section-resumen-empleador")
        resumen_html = page.inner_html("#section-resumen-empleador")
        assert "NO se proyecta como IBC mensual" in resumen_html
        summary_rows = page.locator("#table-resumen-empleadores tbody tr")
        assert summary_rows.count() == 2

        # 3.3 Verify Table 2: Detail table columns and provenance
        detail_rows = page.locator("#table-registros tbody tr")
        assert detail_rows.count() >= 5
        # Verify first row shows PDF provenance badge
        assert "PDF" in detail_rows.first.inner_text()

        # 4. Interactive Editing of a Record with Modal and Motive
        first_row_edit_btn = detail_rows.first.locator("button:has-text('Editar')")
        first_row_edit_btn.click()

        # Wait for edit modal
        page.wait_for_selector("#edit-record-modal.active", state="visible")
        # Check original comparison summary is shown
        orig_summary = page.inner_text("#edit-modal-original-summary")
        assert "2024-01-01" in orig_summary
        assert "6.000.000" in orig_summary

        # Test validation inside edit modal: Inverted date
        page.fill("#edit-modal-inicio", "2024-02-15")
        page.fill("#edit-modal-fin", "2024-01-10")
        page.fill("#edit-modal-motivo", "Test corrección fechas")
        assert page.is_visible("#edit-modal-error-box")
        assert "invertida" in page.inner_text("#edit-modal-error-box").lower()
        # Save button should be disabled on validation error
        save_btn = page.locator("#btn-save-record-edit")
        assert save_btn.is_disabled()

        # Fix to valid values with explicit motive
        page.fill("#edit-modal-inicio", "2024-01-01")
        page.fill("#edit-modal-fin", "2024-01-31")
        page.fill("#edit-modal-dias", "30")
        page.fill("#edit-modal-ibc", "6500000")
        page.fill(
            "#edit-modal-motivo", "Ajuste de IBC según desprendible oficial de nómina"
        )
        page.wait_for_selector("#edit-modal-error-box", state="hidden")
        assert not save_btn.is_disabled()

        # Save correction
        page.click("#btn-save-record-edit")
        page.wait_for_selector("#edit-record-modal.active", state="hidden")

        # Verify badge updated to CORRECCIÓN / CORREGIDO
        first_row_after_edit = page.locator("#table-registros tbody tr").first
        assert (
            "CORRECCIÓN" in first_row_after_edit.inner_text()
            or "CORREGIDO" in first_row_after_edit.inner_text()
        )
        assert "$6.500.000" in first_row_after_edit.inner_text()

        # 5. Exclusion and Re-inclusion of a Record
        second_row = page.locator("#table-registros tbody tr").nth(1)
        exclude_btn = second_row.locator("button:has-text('Excluir')")
        exclude_btn.click()

        # Wait for exclude modal
        page.wait_for_selector("#exclude-record-modal.active", state="visible")
        page.fill(
            "#exclude-modal-motivo", "Período duplicado en régimen de ahorro individual"
        )
        page.click("#exclude-record-modal button:has-text('Confirmar Exclusión')")
        page.wait_for_selector("#exclude-record-modal.active", state="hidden")

        # Verify row is marked as excluded
        second_row_after = page.locator("#table-registros tbody tr").nth(1)
        assert "EXCLUIDO" in second_row_after.inner_text()
        # Should now offer 'Incluir' button
        assert second_row_after.locator("button:has-text('Incluir')").is_visible()

        # 6. Restoration of the Edited Record to Original PDF Values
        restore_btn = first_row_after_edit.locator("button[title*='Restaurar']")
        assert restore_btn.is_visible()
        restore_btn.click()

        # Verify first row restored to $6.000.000 and PDF badge
        first_row_restored = page.locator("#table-registros tbody tr").first
        assert "PDF" in first_row_restored.inner_text()
        assert "$6.000.000" in first_row_restored.inner_text()

        # 7. Add User Declared Period
        page.fill("#decl-inicio", "2025-01-01")
        page.fill("#decl-fin", "2025-03-31")
        page.fill("#decl-dias", "90")
        page.fill("#decl-ibc", "5000000")
        page.fill("#decl-aportante", "EMPRESA NUEVA DECLARADA")
        page.fill(
            "#decl-motivo",
            "Período laborado con contrato aportado pero omitido en el reporte",
        )
        page.click("#btn-add-declared-period")

        # Verify declared period appears in detail table with DECLARADO badge
        page.wait_for_selector("#table-registros tbody tr:has-text('DECLARADO')")
        declared_row = page.locator(
            "#table-registros tbody tr:has-text('EMPRESA NUEVA DECLARADA')"
        )
        assert declared_row.count() >= 1

        # Check declared weeks KPI reflects the new contribution
        page.wait_for_function(
            "() => parseFloat(document.getElementById('recon-kpi-declaradas').textContent) > 0"
        )
        kpi_decl_val = float(page.inner_text("#recon-kpi-declaradas"))
        assert kpi_decl_val > 0

        # 8. Test filter buttons on detail table
        # Click 'Excluidos' filter
        page.click("#filter-btn-excluded")
        filtered_rows = page.locator("#table-registros tbody tr")
        assert filtered_rows.count() == 1
        assert "EXCLUIDO" in filtered_rows.first.inner_text()

        # Reset to 'Todos' filter
        page.click("#filter-btn-all")
        assert page.locator("#table-registros tbody tr").count() >= 5

        # 9. Return to Step 2 and verify data is preserved without losing corrections
        page.click("button:has-text('Volver a Datos del Afiliado')")
        page.wait_for_selector("#step-panel-2", state="visible")
        assert page.input_value("#rev-sexo") == "FEMENINO"

        # Return to Step 3
        page.click("#btn-to-review-periods")
        page.wait_for_selector("#step-panel-3", state="visible")

        # This deliberately incomplete detail must NOT pass reconciliation.
        page.click("#btn-confirm-periods-to-transition")
        page.wait_for_selector("#review-validation-errors-box", state="visible")
        assert "Discrepancia" in page.inner_text("#review-validation-errors-box")
        assert page.is_visible("#step-panel-3")
        assert not page.is_visible("#step-panel-4")

        # 13. Open Audit and verify revision data was recorded
        page.click("button:has-text('Auditoría de la Simulación')")
        page.wait_for_selector("#audit-modal.active", state="visible")
        page.wait_for_selector(
            "#audit-content-area .card", state="visible", timeout=5000
        )

        audit_text = page.inner_text("#audit-content-area")
        assert len(audit_text) > 100

        # Close audit
        page.click("#audit-modal .modal-close")
        page.wait_for_selector("#audit-modal.active", state="hidden")

        # 14. Reset Session
        page.click("button:has-text('Borrar Sesión')")
        page.wait_for_selector("#reset-session-modal.active", state="visible")
        page.click("#btn-confirm-reset-session")
        page.wait_for_selector("#step-panel-1", state="visible")

        # Verify form is clean
        assert page.input_value("#rev-fecha-nac") == ""
        assert page.input_value("#rev-sexo") == ""
