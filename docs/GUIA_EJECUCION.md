# Guía de Instalación, Ejecución y Cierre Local

## 1. Requisitos Previos

- **Sistema Operativo:** Windows 11 / Linux / macOS.
- **Python:** Versión 3.12 o superior (x64).
- **Navegador Web:** Edge, Chrome, Firefox, Safari o Brave.

---

## 2. Iniciar la Aplicación

Ejecute en la terminal de PowerShell:

```powershell
# Ubicarse en el directorio raíz
cd F:\MiPensionCO

# Iniciar el servidor local
python run_app.py
```

El servidor iniciará escuchando **únicamente en la interfaz de bucle invertido local (loopback)**:
```text
======================================================================
🇨🇴  MiPensiónCO — Simulador Pensional de Vejez (Ley 100 / Transición)
======================================================================
Iniciando servidor local en: http://127.0.0.1:8000
Presione Ctrl+C para detener el servidor.
======================================================================
```

Abra su navegador en la dirección: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

## 3. Detener la Aplicación

Para cerrar el servidor, presione `Ctrl + C` en la consola de PowerShell donde se está ejecutando `run_app.py`.

---

## 4. Ejecución de Pruebas y Control de Calidad

Para ejecutar la suite de pruebas unitarias y de integración:

```powershell
# Ejecutar todas las pruebas con detalle
pytest -v

# Verificar cobertura de código (>90%)
pytest -v --cov=src tests/

# Análisis estático estricto de tipos con mypy
mypy --strict src/

# Verificación de linter y formato con ruff
ruff check src/ tests/ run_app.py
```
