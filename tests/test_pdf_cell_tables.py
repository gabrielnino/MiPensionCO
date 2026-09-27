"""Regression for actual cell-based Colpensiones layouts, without personal data."""

from datetime import date
from decimal import Decimal

import fitz

from src.domain.models import HistoriaLaboral
from src.domain.validation import reconcile_labor_history
from src.parser.pdf_reader import ColpensionesPDFReader


def test_cell_based_monthly_table() -> None:
    doc = fitz.open()
    page = doc.new_page(width=1000, height=400)
    headers = [f"[{n}]" for n in range(34, 47)]
    rows = [
        headers,
        [
            "800123456",
            "EMPRESA TEST",
            "NO",
            "200802",
            "07/03/2008",
            "123456789012",
            "$ 100.000",
            "$ 16.000",
            "-$ 144.000",
            "",
            "30",
            "3",
            "Traslado",
        ],
    ]
    for y in (80, 110, 140):
        page.draw_line((20, y), (995, y))
    for i in range(14):
        page.draw_line((20 + i * 75, 80), (20 + i * 75, 140))
    for j, row in enumerate(rows):
        for i, value in enumerate(row):
            page.insert_text((22 + i * 75, 95 + j * 30), value, fontsize=6)
    history, report = ColpensionesPDFReader.extract_from_bytes(doc.tobytes())
    doc.close()
    assert report.success
    assert history is not None
    assert len(history.registros) == 1
    record = history.registros[0]
    assert record.periodo_inicio == date(2008, 2, 1)
    assert record.periodo_fin == date(2008, 2, 29)
    assert record.ibc == Decimal(100000)
    assert record.dias_reportados == 30
    assert record.dias_cotizados == 3
    assert record.fecha_pago == date(2008, 3, 7)
    assert record.source_fragment_ids


def test_empty_detail_is_never_reconciled() -> None:
    result = reconcile_labor_history(HistoriaLaboral("SYNTHETIC"))
    assert not result["permite_continuar"]
    assert result["errores_bloqueantes"]


def test_affiliate_fields_follow_visual_order_not_pdf_object_order() -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((230, 100), "26/03/1981")
    page.insert_text((230, 130), "30 agosto 2025")
    page.insert_text((30, 100), "Fecha de Nacimiento:")
    page.insert_text((30, 130), "ACTUALIZADO A:")
    history, _ = ColpensionesPDFReader.extract_from_bytes(doc.tobytes())
    doc.close()
    assert history.fecha_nacimiento == date(1981, 3, 26)
    assert history.fecha_actualizacion_reporte == date(2025, 8, 30)
