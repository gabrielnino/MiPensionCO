# HARNESS DE OPERACIÓN Y CONTROL: MiPensiónCO

## 1. Ficha Técnica del Proyecto Local

| Parámetro | Valor Actual | Notas |
| :--- | :--- | :--- |
| **Nombre del Proyecto** | `MiPensiónCO` | Simulador y motor de reglas pensionales de Colombia |
| **Directorio Local Primario** | `F:\MiPensionCO` | Espacio de trabajo local principal |
| **Versión Runtime** | Python 3.12+ (x64) | Tipado estricto con `mypy`, formateo con `ruff` |
| **Harness Disciplinario** | Conforme a `AGENTS.md` | TDD (pytest), Clean Code, SOLID, desarrollo local |
| **Marco Normativo Base** | Sistema Pensional Colombiano | Ley 100/1993, Ley 797/2003, Ley 2381/2024 (Pilares) |
| **Almacenamiento Local** | SQLite / Modelos en memoria | Sin dependencias de bases de datos o servicios remotos |

---

## 2. Principios del Entorno Local

1. **Autocontenido:** Toda la lógica de negocio, pruebas y simulaciones se ejecutan de manera local e independiente, sin requerir servidores VPS, brokers remotos ni conexiones a la nube obligatorias.
2. **Determinismo y TDD:** Toda regla legal y financiera (edad de jubilación, cálculo de IBL, tasa de reemplazo, reducción progresiva de semanas para mujeres) debe estar respaldada por pruebas unitarias automatizadas (`pytest`) antes de su implementación en producción.
3. **Manejo de Errores y Tipado Estricto:** Excepciones de dominio claras (`PensionCalculationError`, etc.) y 100% de anotaciones de tipo estáticas validadas con `mypy`.
4. **Seguridad y Secretos Locales:** Los parámetros y claves de configuración residen en archivos locales `.env` o en la carpeta `config/`, protegidos por `.gitignore`.

---

## 3. Hoja de Ruta de Desarrollo Local (Roadmap)

- [x] **Fase 0: Inicialización y Gobernanza Local**
  - [x] Estructura base del repositorio en `F:\MiPensionCO`.
  - [x] Configuración de `.gitignore` para entorno Python/Node local.
  - [x] Adopción del harness de ingeniería local (`AGENTS.md` y `HARNESS.md`).
  - [x] Definición de objetivos del simulador en `README.md`.

- [ ] **Fase 1: Modelado de Dominio y Parámetros Legales (Core)**
  - [ ] Modelos de datos inmutables y tipados (`src/models/`): perfil del cotizante, historial de semanas, IBL, factores de ajuste.
  - [ ] Tabla de constantes legales históricas y vigentes (SMLMV por año, IPC, umbrales de pilares).
  - [ ] Jerarquía de excepciones de dominio (`src/core/exceptions.py`).

- [ ] **Fase 2: Motor de Reglas Pensionales (TDD)**
  - [ ] **Régimen de Prima Media (Colpensiones):** 1.300 semanas base, edad (57M / 62H), cálculo de tasa de reemplazo (65.5% - 80%), reducción progresiva de semanas para mujeres.
  - [ ] **Régimen de Ahorro Individual (Fondos Privados - RAIS):** Capital acumulado, garantía de pensión mínima (1.150 semanas).
  - [ ] **Nuevo Sistema de Pilares (Ley 2381 de 2024):** Pilar Solidario, Semicontributivo, Contributivo (tope 2.3 SMLMV en Colpensiones + excedente en fondo privado) y Ahorro Voluntario.
  - [ ] **Diagnóstico de Transición:** Verificación automática de cumplimiento de semanas a julio de 2025 (750 mujeres / 900 hombres).

- [ ] **Fase 3: Interfaz y Presentación Local**
  - [ ] CLI interactivo para simulaciones rápidas en consola.
  - [ ] Interfaz gráfica local / web ligera para visualización de escenarios comparativos.
  - [ ] Exportación de reportes de proyección pensional (formato JSON y Markdown).

---

## 4. Comandos de Verificación Local

```powershell
# Ejecutar suite de pruebas unitarias
pytest -v

# Validar cobertura de código
pytest --cov=src tests/

# Análisis estático de tipos
mypy --strict src/

# Formato y linter
ruff check src/ tests/
ruff format src/ tests/
```
