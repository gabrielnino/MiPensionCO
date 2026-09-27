# MiPensiónCO 🇨🇴

**Simulador Pensional Ordinario Local para Afiliados a Colpensiones en Régimen de Transición (Ley 100 de 1993)**

---

## 🎯 Descripción General

**MiPensiónCO** es una aplicación web local, determinista y respetuosa de la privacidad, diseñada para simular la pensión ordinaria de vejez de afiliados a Colpensiones que conservan las reglas de la Ley 100 de 1993 y sus modificaciones (Ley 797 de 2003), conforme al artículo 75 de la Ley 2381 de 2024 y la modulación jurisprudencial de la Sentencia **C-264 de 2026** de la Corte Constitucional.

> **AVISO LEGAL:**  
> Estimación puramente informativa basada en los datos documentales y supuestos indicados. El reconocimiento y liquidación pensional corresponden exclusivamente a Colpensiones.

---

## 🚀 Inicio Rápido

```powershell
# 1. Iniciar el servidor local
python run_app.py

# 2. Abrir en el navegador:
# http://127.0.0.1:8000
```

---

## 🔒 Privacidad y Funcionamiento Local

- **100% Local:** Todo el procesamiento de los PDFs, los cálculos del IBL, el cómputo de semanas y la proyección se realizan en la memoria de su equipo.
- **Sin Dependencias Cloud:** No utiliza servicios de inteligencia artificial externos, OCR en la nube ni telemetría.
- **Sin Cuentas ni Registro:** No requiere creación de usuario ni almacena contraseñas de PDFs en disco o logs.
- **Borrado de Sesión:** Permite purgar la información en memoria con un solo clic.

---

## 📚 Documentación Técnica y Jurídica

- **[Cálculo y Límites Legales](docs/CALCULO_Y_LIMITES.md):** Metodología matemática y jurídica detallada (IBL 10 años vs toda la vida, tasa de reemplazo, garantía de pensión mínima, tope de 25 SMLMV, descuentos de salud y FSP).
- **[Catálogo Jurídico](docs/CATALOGO_JURIDICO.md):** 14 reglas jurídicas verificadas con sus artículos, sentencias oficiales y estado de validación.
- **[Tablas Económicas Oficiales](docs/TABLAS_ECONOMICAS.md):** Decretos de SMLMV (1990-2026) e IPC de empalme oficial DANE (1990-2026).
- **[Guía de Ejecución y Pruebas](docs/GUIA_EJECUCION.md):** Comandos de inicio, cierre y verificación de calidad con `pytest`, `mypy` y `ruff`.

---

## 🧪 Pruebas Automatizadas y Calidad

```powershell
# Ejecutar 33 pruebas unitarias y de integración
pytest -v

# Cobertura de código (>90%)
pytest -v --cov=src tests/

# Análisis estático de tipos
mypy --strict src/

# Linter y estilo
ruff check src/ tests/ run_app.py
```
