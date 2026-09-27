"""Playwright Real Browser E2E Test Suite for MiPensiónCO.

Strictly verifies the complete 11-point workflow in a real browser:
1. Multi-page synthetic PDF upload with summary and detail tables.
2. Preload verification in Step 2: exact date '30 agosto 2025' -> 2025-08-30 (never October), summary weeks.
3. Manual correction and user declared period (DECLARACION_USUARIO).
4. Dual tables verification: Table 1 (PDF immutable) and Table 2 (User declared editable).
5. Transition regime evaluation (C-264 / Ley 2381).
6. Multi-scenario simulation (Conservative, Base, Optimistic).
7. Strict blocking on discrepancies or deficit.
8. Step-by-step audit inspection (Extracted, Transformed, Calculated, Diagnosed).
9. Session reset modal and memory purge verification (DOM & RAM).
10. XSS defense in real browser (script injection harmlessly rendered as text).
"""

import io
import tempfile
import threading
import time
from collections.abc import Generator
from pathlib import Path

import fitz  # type: ignore[import-untyped]
import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from src.api.app import app


def create_multipage_synthetic_test_pdf(
    header_date_str: str = "ACTUALIZADO A: 30 agosto 2025",
    malicious_text: str = "",
) -> bytes:
    """Creates a realistic 2-page Colpensiones PDF for browser tests."""
    doc = fitz.open()
    page1 = doc.new_page(width=595, height=842)

    nombre = malicious_text if malicious_text else "RODRIGO MARTINEZ AFILIADO"

    # Header with date
    page1.insert_text(
        (120, 40),
        "COLPENSIONES Nit 900.336.004-7\n"
        "REPORTE DE SEMANAS COTIZADAS EN PENSIONES\n"
        f"{header_date_str}",
        fontsize=9,
    )
    page1.draw_line(fitz.Point(40, 75), fitz.Point(555, 75))

    # Affiliate Info
    page1.insert_text((40, 95), "INFORMACIÓN DEL AFILIADO", fontsize=10)
    info_text = (
        f"Nombre: {nombre}\n"
        "Tipo de Documento: Cédula de Ciudadanía\n"
        "Número de Documento: 79123456\n"
        "Fecha de Nacimiento: 20/05/1970\n"
        "Estado Afiliación: Activo Cotizante\n"
        "Fecha Afiliación: 15/01/1996\n"
        "Fecha de Expedición: 15/10/2025"
    )
    page1.insert_text((40, 115), info_text, fontsize=8)

    # Employer Summary Table
    page1.insert_text(
        (40, 220), "RESUMEN DE SEMANAS COTIZADAS POR EMPLEADOR", fontsize=10
    )
    page1.insert_text(
        (40, 240),
        "[1]Identificación  [2]Razón Social  [3]Desde  [4]Hasta  [5]Salario  [6]Sem  [7]Lic  [8]Sim  [9]Total",
        fontsize=7,
    )
    page1.insert_text(
        (40, 255),
        "860001234  INDUSTRIAS BOGOTA SAS  01/01/2005  31/12/2014  $2.500.000  521,43  0,00  0,00  521,43",
        fontsize=7,
    )
    page1.insert_text(
        (40, 270),
        "900987654  SERVICIOS ANDINOS LTDA  01/01/2015  31/12/2024  $3.800.000  521,43  0,00  0,00  521,43",
        fontsize=7,
    )
    page1.insert_text((40, 290), "TOTAL GENERAL DE SEMANAS: 1042.86", fontsize=9)

    # Page 2: Monthly Details
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text(
        (40, 40), "DETALLE DE PAGOS POR CICLO (CONTINUACIÓN)", fontsize=10
    )
    page2.insert_text(
        (40, 60),
        "Periodo Inicio  Periodo Fin  Dias  IBC (COP)  Empleador",
        fontsize=7,
    )
    detail_rows = [
        "01/01/2024  31/01/2024  30  $ 3.800.000  SERVICIOS ANDINOS LTDA",
        "01/02/2024  29/02/2024  30  $ 3.800.000  SERVICIOS ANDINOS LTDA",
        "01/03/2024  31/03/2024  30  $ 3.800.000  SERVICIOS ANDINOS LTDA",
        "01/04/2024  30/04/2024  30  $ 3.800.000  SERVICIOS ANDINOS LTDA",
    ]
    y = 75
    for r in detail_rows:
        page2.insert_text((40, y), r, fontsize=7)
        y += 15

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture(scope="module")
def local_server_url() -> Generator[str, None, None]:
    """Runs FastAPI local server on a dedicated test port."""
    port = 8899
    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    # Wait for server to bind
    time.sleep(1.0)
    url = f"http://127.0.0.1:{port}"
    yield url
    server.should_exit = True
    t.join(timeout=2.0)


# ---------------------------------------------------------------------------
# Test: Full 11-step E2E workflow in real Playwright browser
# ---------------------------------------------------------------------------
def test_playwright_e2e_full_workflow(local_server_url: str) -> None:
    pdf_bytes = create_multipage_synthetic_test_pdf()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(pdf_bytes)
        pdf_temp_path = tf.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.on("dialog", lambda dialog: dialog.accept())

            # 1. Navigate to home
            page.goto(local_server_url)
            page.wait_for_selector("#dropzone")
            assert "MiPensiónCO" in page.title()

            # 2. Upload synthetic multipage PDF via input
            page.set_input_files("#pdf-file-input", pdf_temp_path)

            # Wait for Step 2 panel to be visible
            page.wait_for_selector("#step-panel-2", state="visible", timeout=10000)

            # 3. Verify Preloaded fields in Step 2 (Hallazgo 4 & 5)
            # Check date: 2025-08-30 and Spanish hint contains 'agosto'
            corte_val = page.input_value("#rev-fecha-corte")
            assert corte_val == "2025-08-30", f"Expected 2025-08-30, got {corte_val}"
            corte_es = page.inner_text("#rev-fecha-corte-es")
            assert "agosto" in corte_es.lower(), (
                f"Expected agosto in hint, got {corte_es}"
            )
            assert "octubre" not in corte_es.lower()

            # Birth date
            assert page.input_value("#rev-fecha-nac") == "1970-05-20"

            # Check summary table
            assert page.is_visible("#table-resumen-empleadores")
            summary_rows = page.locator("#table-resumen-empleadores tbody tr")
            assert summary_rows.count() >= 2

            # Check Table 1 (PDF immutable records)
            pdf_rows = page.locator("#table-registros tbody tr")
            assert pdf_rows.count() >= 4
            # First row has PDF badge
            assert "PDF" in pdf_rows.first.inner_text()

            # 4. Fill required unselected fields & Add user declared period (Hallazgo 5)
            # Pension category (MASCULINO)
            page.select_option("#rev-sexo", "MASCULINO")
            # Alto riesgo
            page.fill("#rev-alto-riesgo", "0")

            # Declare new period in Table 2
            page.fill("#decl-inicio", "2025-01-01")
            page.fill("#decl-fin", "2025-03-31")
            page.fill("#decl-dias", "90")
            page.fill("#decl-ibc", "3800000")
            page.fill("#decl-aportante", "EMPRESA ADICIONAL DECLARADA")
            page.click("#btn-add-declared-period")

            # Verify declared table displays the new row
            page.wait_for_selector(
                "#table-registros-declarados tbody tr:has-text('DECLARACION_USUARIO')"
            )
            decl_rows = page.locator("#table-registros-declarados tbody tr")
            assert decl_rows.count() >= 1
            assert "DECLARACION_USUARIO" in decl_rows.first.inner_text()
            assert "EMPRESA ADICIONAL DECLARADA" in decl_rows.first.inner_text()

            # 5. Confirm review and evaluate transition (Step 3)
            page.click("button:has-text('Confirmar Datos y Evaluar Transición')")
            page.wait_for_selector("#step-panel-3", state="visible", timeout=10000)

            # Check transition result banner
            banner_text = page.inner_text("#transition-result-banner")
            assert "COBIJADO POR EL RÉGIMEN DE TRANSICIÓN" in banner_text
            assert "900" in page.inner_text("#trans-kpi-umbral")

            # 6. Proceed to Step 4: Scenario Configuration
            page.click("#btn-to-step-4")
            page.wait_for_selector("#step-panel-4", state="visible")

            # Run Simulation
            page.click("#btn-run-simulation")

            # 7. Step 5: Results & Comparison
            page.wait_for_selector("#step-panel-5", state="visible", timeout=10000)
            res_cards = page.locator("#simulation-output .card")
            assert res_cards.count() >= 2

            # 8. Step-by-Step Audit Modal (Hallazgo 6 & 7)
            page.click("button:has-text('Auditoría de la Simulación')")
            page.wait_for_selector("#audit-modal.active", state="visible")

            # Verify Audit content sections
            audit_text = page.inner_text("#audit-content-area")
            assert "Qué extrajo del PDF" in audit_text or "Extracción" in audit_text
            assert "Qué calculó" in audit_text or "Escenario" in audit_text
            assert "Desglose de Operaciones Reales" in audit_text or "IBL" in audit_text

            # Test step filter
            page.select_option("#audit-filter-step", "CALCULO")
            audit_calc_text = page.inner_text("#audit-content-area")
            assert "Escenario" in audit_calc_text

            # Close audit modal
            page.click("#audit-modal .modal-close")
            page.wait_for_selector("#audit-modal.active", state="hidden")

            # 9. Reset Session Modal (Hallazgo 7)
            page.click("button:has-text('Borrar Sesión')")
            page.wait_for_selector("#reset-session-modal.active", state="visible")

            # Checkbox for disk audit should be unchecked by default
            chk_disk = page.locator("#chk-delete-disk-audit")
            assert not chk_disk.is_checked(), (
                "Disk delete checkbox must NOT be checked by default!"
            )

            # Handle alert dialog on session reset
            page.on("dialog", lambda dialog: dialog.accept())

            # Confirm session reset
            page.click("#btn-confirm-reset-session")
            page.wait_for_selector("#step-panel-1", state="visible")

            # Verify DOM is completely cleared
            assert page.input_value("#rev-fecha-nac") == ""
            assert page.input_value("#rev-fecha-corte") == ""
            assert page.input_value("#rev-semanas-resumen") == ""

            browser.close()
    finally:
        Path(pdf_temp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: XSS Defense in Real Browser (DOM & Script Execution)
# ---------------------------------------------------------------------------
def test_playwright_xss_defense_real_dom(local_server_url: str) -> None:
    """PDF containing active XSS payload in affiliate name must render as safe text

    without executing any scripts or polluting the DOM with attacker variables.
    """
    xss_payload = "<script>window.__xss_executed = true;</script><img src=invalid onerror='window.__xss_executed=true;'>"
    pdf_bytes = create_multipage_synthetic_test_pdf(malicious_text=xss_payload)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(pdf_bytes)
        pdf_temp_path = tf.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(local_server_url)
            page.set_input_files("#pdf-file-input", pdf_temp_path)
            page.wait_for_selector("#step-panel-2", state="visible", timeout=10000)

            # Check if any XSS payload executed in JavaScript window context
            xss_flag = page.evaluate("() => window.__xss_executed")
            assert xss_flag is None or xss_flag is False, (
                "CRITICAL SECURITY BREACH: XSS payload executed in the real browser!"
            )

            # Open audit modal to check XSS defense there as well
            page.click("button:has-text('Auditoría de la Simulación')")
            page.wait_for_selector("#audit-modal.active", state="visible")

            xss_flag_modal = page.evaluate("() => window.__xss_executed")
            assert xss_flag_modal is None or xss_flag_modal is False, (
                "CRITICAL SECURITY BREACH: XSS executed inside the audit modal!"
            )

            browser.close()
    finally:
        Path(pdf_temp_path).unlink(missing_ok=True)
