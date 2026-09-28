# Sistema de Auditoría y Trazabilidad Paso a Paso

El sistema de auditoría de **MiPensiónCO** garantiza la transparencia algorítmica y la explicabilidad jurídica completa del proceso pensional, protegiendo estrictamente la privacidad del afiliado mediante una arquitectura desacoplada en dos niveles.

---

## 1. Arquitectura en Dos Niveles

```mermaid
flowchart TD
    subgraph Nivel1["Nivel 1: Registro Técnico de Eventos (Sin PII)"]
        T1[Operaciones del Sistema\nDuración, Estado, Eventos] --> T2[logs/technical_audit.log]
        T2 -.-> T3[Cero Salarios, Cero Nombres, Cero Cédulas\nIdentificador Opaco y Mensajes Estáticos]
    end

    subgraph Nivel2["Nivel 2: Auditoría Documental y de Cálculo (En Memoria por Defecto)"]
        D1[Extracción PDF por Página\nTexto Crudo y Fragmentos con Coordenadas] --> D2[Memoria Volátil: DocumentAuditRecord v2.1.0]
        D3[Correcciones de Usuario con Motivo] --> D2
        D4[Evaluación de Transición C-264] --> D2
        D5[Cálculos IBL, Semanas y Mesadas por Escenario] --> D2
        D2 --> D6{¿Usuario Habilitó Guardado Local?}
        D6 -- Sí --> D7[audit/audit_execution_id.json\nEscritura Atómica Segura (Sin guardar el PDF)]
        D6 -- No --> D8[Permanece estrictamente en RAM]
        D2 --> D9[Exportación JSON / Reporte Markdown / Visor UI]
    end

    subgraph Purga["Purga de Privacidad"]
        P1[POST /api/reset-session] --> P2[Limpieza total de memoria y borrado de archivos locales en audit/]
    end
```

### Nivel 1: Registro Técnico de Eventos (Sin PII)
- **Destino:** `logs/technical_audit.log`.
- **Formato:** `[ISO_TIMESTAMP] [SEVERITY] [EXEC_ID] [STEP] [EVENT_CODE] Status: STATUS (DUR_MS) - MESSAGE | Acción: ACTION`.
- **Garantía Estricta:** Jamás incluye nombres de personas o empresas, números de documento, semanas acumuladas, valores de IBC ni montos de mesada. Las llamadas a `AuditService.log_technical` utilizan mensajes estáticos controlados y sanitización obligatoria de cualquier residuo monetario.

### Nivel 2: Auditoría Documental y de Cálculo
- **Destino por Defecto:** Memoria de sesión activa (`AuditService._active_audits`).
- **Persistencia Voluntaria:** Se realiza únicamente cuando el usuario lo solicita explícitamente (`POST /api/audit/{id}/save-local`), guardándose atómicamente en `audit/audit_<id>.json`. **Bajo ninguna circunstancia se almacena el archivo binario del PDF original.**
- **Exportación:** Accesible en cualquier momento vía `GET /api/audit/{id}/export` (JSON) o `GET /api/audit/{id}/report.md` (Markdown diagnóstico).
- **Purga Total:** `POST /api/reset-session?execution_id={id}&delete_persisted_audit=true` elimina el estado en RAM y borra el archivo JSON persistido en disco.

---

## 2. Esquema de Datos Versionado (`DocumentAuditRecord` v2.1.0)

El modelo de auditoría serializa importes y semanas como cadenas numéricas exactas (`str`), no como `float`, para garantizar reproducibilidad financiera y evitar imprecisiones de redondeo en punto flotante:

```json
{
  "execution_id": "test-e2e-exec-001",
  "schema_version": "2.1.0",
  "created_at_iso": "2026-09-27T20:45:00.000000+00:00",
  "document_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "total_pages": 1,
  "pages_processed": 1,
  "pages_audit": [
    {
      "page_number": 1,
      "method": "TEXTO_DIRECTO",
      "text_length": 450,
      "fragments_detected": 12,
      "raw_page_text": "COLPENSIONES - HISTORIA LABORAL...",
      "fragments": [
        {
          "fragment_id": "p1_f1",
          "page_number": 1,
          "order": 1,
          "raw_text": "01/01/2024 31/01/2024 30 $ 3.000.000 EMPRESA S.A.S.",
          "coordinates": [50.0, 120.0, 550.0, 135.0],
          "status": "INTERPRETADO",
          "explanation": "Registro de cotización normalizado exitosamente"
        }
      ],
      "uninterpreted_lines": [],
      "limitations": []
    }
  ],
  "extraction_status": "COMPLETA",
  "detected_fields": [
    {
      "field_name": "semanas_resumen_colpensiones",
      "raw_text": "Total Semanas Cotizadas: 950.00",
      "parsed_value": "950.00",
      "unit": "semanas",
      "provenance": "PDF_RESUMEN",
      "validation_status": "VERIFICADO",
      "explanation": "Total consolidado por Colpensiones",
      "source_fragment_ids": ["p1_f0"]
    }
  ],
  "user_corrections": [
    {
      "field_name": "registros[0].ibc",
      "original_value": "3000000",
      "corrected_value": "3500000",
      "reason": "Ajuste conforme a planilla PILA adjunta soporte",
      "provenance": "DECLARACION_USUARIO",
      "timestamp_iso": "2026-09-27T20:46:00.000000+00:00",
      "order": 1,
      "invalidated_evaluations": ["transition_evaluation", "scenario_simulations"]
    }
  ],
  "documentary_discrepancies": [],
  "transition_audit": {
    "rule_applied": "Ley 2381 de 2024, Art. 75",
    "cutoff_date": "2027-04-01",
    "threshold_required": 900,
    "weeks_at_cutoff": "950.00",
    "status": "EVIDENCIA_SUFICIENTE_CUMPLIMIENTO",
    "permits_continuation": true,
    "explanation": "Acredita 950.00 semanas frente a 900 exigidas al corte del 1 de abril de 2027."
  },
  "scenarios_audit": [
    {
      "scenario_id": "esc_base",
      "scenario_name": "Escenario Base",
      "fixed_horizon_date": "2034-05-15",
      "legal_retirement_age": 62,
      "inputs": {
        "ibc_futuro": "3500000",
        "fecha_inicio": "2026-01-01",
        "crecimiento": "0.05"
      },
      "generated_future_periods_count": 92,
      "weeks_breakdown": {
        "documentales": "950.00",
        "calendario": "950.00",
        "proyectadas": "394.28",
        "totales": "1344.28",
        "exigidas": "1300",
        "deficit": "0.00"
      },
      "effective_contributions_selected": [
        {
          "index": 1,
          "periodo": "2034-04-01 a 2034-04-30",
          "dias_calendario": 30,
          "ibc_nominal": "5170889",
          "ipc_periodo": "142.15",
          "ipc_retiro": "142.15",
          "factor_actualizacion": "1.0000",
          "ibc_actualizado": "5170889",
          "origen": "SUPUESTO"
        }
      ],
      "ibl_method_chosen": "ULTIMOS_10_ANOS",
      "ibl_final": "4250000",
      "smlmv_ref": "2500000",
      "s_factor": "1.7000",
      "replacement_rate_initial_pct": "64.65",
      "additional_weeks_blocks": 0,
      "replacement_rate_final_pct": "64.65",
      "gross_pension": "2747625",
      "limit_applied": "NINGUNO",
      "health_discount_pct": "10.00",
      "health_discount_amount": "274763",
      "fsp_discount_pct": "0.00",
      "fsp_discount_amount": "0",
      "net_pension_after_discounts": "2472862",
      "real_purchasing_power_cop": "2472862",
      "smlmv_multiples": "1.70",
      "is_blocked": false,
      "blocking_reason": null,
      "step_by_step_operations": [
        "Horizonte ordinario: 2034-05-15 (cumplimiento de 62 años).",
        "Requisito legal aplicable (2034): 1300 semanas.",
        "Semanas reconocidas documentales: 950.00. Semanas recalculadas: 950.00.",
        "Semanas proyectadas hasta la edad legal: 394.28.",
        "Total semanas a la edad legal: 1344.28.",
        "IBL últimos 10 años cotizados: $4,250,000 COP.",
        "Tasa de reemplazo inicial s=1.70: 64.65%.",
        "Mesada bruta: $2,747,625 COP.",
        "Descuento salud (10%): $274,763 COP.",
        "Mesada neta estimada: $2,472,862 COP."
      ]
    }
  ],
  "sensitive_save_enabled": true
}
```

---

## 3. Códigos de Eventos Técnicos (`EventCode`)

| Código de Evento | Severidad Habitual | Significado Operativo |
| :--- | :--- | :--- |
| `PDF_CARGADO` | `INFO` | Documento PDF procesado correctamente con capas de texto legibles. |
| `PDF_VACIO` | `ADVERTENCIA` | Documento escaneado sin texto o completamente en blanco. |
| `PDF_PROTEGIDO_CLAVE` | `ADVERTENCIA` | Archivo PDF requiere contraseña de apertura. |
| `PDF_CORRUPTO` | `ERROR` | Archivo incompleto o con cabeceras dañadas. |
| `IBC_AMBIGUO` | `ADVERTENCIA` | Fila con montos ambiguos no identificables con certeza. |
| `COBERTURA_PARCIAL_INCIERTA` | `ADVERTENCIA` | Días cotizados no especificados explícitamente en el registro. |
| `SIMULTANEIDAD_DETECTADA` | `INFO` | Más de un aportante en el mismo mes calendario; unificados según Ley 100. |
| `DISCREPANCIA_RESUMEN_DETALLE` | `ADVERTENCIA` | Diferencia entre semanas del encabezado y la suma de días calendario. |
| `IPC_FALTANTE` | `BLOQUEADO` | Dato mensual del IPC no disponible en la serie oficial DANE. |
| `TRANSICION_EVIDENCIA_SUFICIENTE` | `INFO` | Acredita umbral antes del 1 de abril de 2027; conserva Ley 100. |
| `DEFICIT_SEMANAS_HORIZONTE` | `INFO` | Déficit de semanas a la edad ordinaria; mesada no reconocida. |
| `SIMULACION_COMPLETADA` | `INFO` | Liquidación de escenario completada exitosamente. |
| `SESION_BORRADA` | `INFO` | Datos de sesión y archivos de auditoría purgados. |
