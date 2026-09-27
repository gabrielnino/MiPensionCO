"""Synthetic Colpensiones PDF Generator for testing.

Generates realistic mock labor history PDFs without PII.
Allows creating encrypted, multi-page, or edge-case test documents.
"""

import io

import fitz  # type: ignore[import-untyped]


def create_synthetic_colpensiones_pdf(
    cedula: str = "12345678",
    nombre: str = "AFILIADO PRUEBA SINTETICA",
    fecha_nacimiento: str = "15/05/1968",
    sexo: str = "MASCULINO",
    fecha_afiliacion: str = "01/02/1995",
    fecha_expedicion: str = "15/08/2025",
    estado: str = "ACTIVO",
    total_semanas: str = "910.43",
    alto_riesgo: str = "0",
    password: str | None = None,
    records_lines: list[str] | None = None,
) -> bytes:
    """Generates an in-memory synthetic PDF mimicking a Colpensiones labor history report."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    text = f"""
ADMINISTRADORA COLOMBIANA DE PENSIONES - COLPENSIONES
HISTORIA LABORAL UNIFICADA - CERTIFICADO DE INFORMACION LABORAL

INFORMACION DEL AFILIADO
Numero de Documento: CC {cedula}
Nombre del Afiliado: {nombre}
Fecha de Nacimiento: {fecha_nacimiento}
Sexo: {sexo}
Estado de Afiliacion: {estado}
Fecha de Afiliacion: {fecha_afiliacion}
Fecha de Expedicion: {fecha_expedicion}

RESUMEN DE COTIZACIONES RECONOCIDAS
Total Semanas: {total_semanas}
Semanas de Alto Riesgo: {alto_riesgo}
Tiempos Publicos: 0.00

DETALLE DE PERIODOS COTIZADOS
Periodo Inicio | Periodo Fin | Dias | IBC (COP) | Empleador
"""
    if records_lines:
        for line in records_lines:
            text += line + "\n"
    else:
        text += """
01/01/2024 31/01/2024 30 $ 2.600.000 EMPRESA NACIONAL DE COLOMBIA
01/02/2024 29/02/2024 30 $ 2.600.000 EMPRESA NACIONAL DE COLOMBIA
01/03/2024 31/03/2024 30 $ 2.600.000 EMPRESA NACIONAL DE COLOMBIA
01/04/2024 30/04/2024 30 $ 2.600.000 EMPRESA NACIONAL DE COLOMBIA
01/05/2024 31/05/2024 30 $ 2.600.000 EMPRESA NACIONAL DE COLOMBIA
01/06/2024 30/06/2024 30 $ 2.600.000 EMPRESA NACIONAL DE COLOMBIA
"""

    page.insert_text((50, 60), text, fontsize=9)

    # Save to buffer
    buf = io.BytesIO()
    if password:
        # Encrypt document
        perm = fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT
        encrypt_meth = fitz.PDF_ENCRYPT_AES_256
        doc.save(
            buf,
            encryption=encrypt_meth,
            user_pw=password,
            owner_pw="adminpass",
            permissions=perm,
        )
    else:
        doc.save(buf)

    doc.close()
    return buf.getvalue()
