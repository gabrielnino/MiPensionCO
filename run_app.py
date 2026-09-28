#!/usr/bin/env python3
"""Runner script for MiPensiónCO Local Web Application.

Binds exclusively to local loopback (127.0.0.1:8000).
"""

import uvicorn


def main() -> None:
    print("=" * 70)
    print("🇨🇴  MiPensiónCO — Simulador Pensional de Vejez (Ley 100 / Transición)")
    print("=" * 70)
    print("Iniciando servidor local en: http://127.0.0.1:8000")
    print("Presione Ctrl+C para detener el servidor.")
    print("=" * 70)
    uvicorn.run(
        "src.api.app:app", host="127.0.0.1", port=8000, reload=False, log_level="info"
    )


if __name__ == "__main__":
    main()
