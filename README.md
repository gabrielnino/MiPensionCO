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

- **[Matriz de Corrección de Hallazgos](docs/MATRIZ_HALLAZGOS.md):** Trazabilidad completa de los hallazgos 2.1–2.10 y problemas pendientes A–I corregidos, su sustento jurídico/técnico y sus pruebas TDD de verificación.
- **[Auditoría y Trazabilidad](docs/AUDITORIA_Y_TRAZABILIDAD.md):** Arquitectura en dos niveles (logs técnicos sin PII vs auditoría de cálculo y documental v2.1.0 en memoria), visor interactivo con coordenadas de fragmentos y exportación JSON/Markdown.
- **[Cálculo y Límites Legales](docs/CALCULO_Y_LIMITES.md):** Metodología matemática y jurídica detallada (IBL 10 años vs toda la vida, unificación de empleadores simultáneos, tasa de reemplazo, garantía de pensión mínima, tope de 25 SMLMV, pausas parciales, horizonte de edad y manejo estricto de IPC).
- **[Catálogo Jurídico](docs/CATALOGO_JURIDICO.md):** 14 reglas jurídicas verificadas con sus artículos, sentencias oficiales y estado de validación.
- **[Tablas Económicas Oficiales](docs/TABLAS_ECONOMICAS.md):** Decretos de SMLMV (1990-2026: Decreto 159 de 2026 = $1.750.905) e IPC de empalme oficial DANE mensual (1990-2026).
- **[Guía de Ejecución y Pruebas](docs/GUIA_EJECUCION.md):** Comandos de inicio, cierre y verificación de calidad con `pytest`, `mypy` y `ruff`.

---

## 🧪 Pruebas Automatizadas y Calidad

```powershell
# Ejecutar las 70 pruebas unitarias, de integración, E2E y de reproducción TDD
pytest -v

# Cobertura de código (93%)
pytest -v --cov=src tests/

# Análisis estático de tipos estricto (0 errores en 19 archivos)
mypy --strict src/

# Linter y estilo sin advertencias
ruff check src/ tests/ run_app.py
```

---

## 🛡️ Procedimiento de Reversión Segura (Rollback)

Todas las modificaciones fueron desarrolladas en la rama aislada `feature/complete-audit-and-corrections` partiendo de la línea base en el commit `cb94827`.
Asimismo, existe un respaldo físico previo en `backups/pre_pending_fixes_cb94827/`.

Para revertir exclusivamente los cambios introducidos por esta revisión y volver a la línea base:
```powershell
git checkout feature/audit-and-findings-fix
# o si se desea descartar la rama de cambios:
git checkout cb94827
```
