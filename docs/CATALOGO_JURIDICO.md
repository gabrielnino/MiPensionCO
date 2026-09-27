# Catálogo de Reglas Jurídicas y Jurisprudencia

**Fecha de Auditoría Base:** 27 de septiembre de 2026.  
**Entorno de Ejecución:** Módulo desacoplado en `src/legal/catalog.py`.

---

| ID Regla | Norma / Sentencia | Fuente Oficial | Período de Aplicación | Parámetros Clave | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RULE-TRANS-2381-ART75` | Ley 2381 de 2024, Art. 75 | [Colpensiones](https://normativa.colpensiones.gov.co/compilacion/docs/ley_2381_2024.htm) | Entrada en vigor del sistema | 750 sem (M) / 900 sem (H) | `VERIFICADA` |
| `RULE-CONST-C264-2026` | Corte Constitucional, C-264 de 2026 | [Corte Constitucional](https://www.corteconstitucional.gov.co/relatoria/2026/C-264-26.htm) | Vigencia modulada (01/04/2027) | Diferimiento de vigencia para disposiciones exequibles | `VERIFICADA` |
| `RULE-TRANS-TRASLADO-ART76` | Ley 2381 de 2024, Art. 76 | [Colpensiones](https://normativa.colpensiones.gov.co/compilacion/docs/ley_2381_2024.htm) | Ventana 2 años | No aplica para afiliados que ya pertenecen a Colpensiones | `VERIFICADA` |
| `RULE-RETIREMENT-AGE-L797` | Ley 797 de 2003, Art. 9 | [Colpensiones](https://normativa.colpensiones.gov.co/compilacion/docs/ley_0797_2003.htm) | 2014 en adelante | 57 años (M) / 62 años (H); 1.300 semanas ordinarias | `VERIFICADA` |
| `RULE-WOMEN-REDUCTION-C197` | Corte Constitucional, C-197 de 2023 | [Corte Constitucional](https://normativa.colpensiones.gov.co/compilacion/docs/C-197_2023.htm) | 2026 a 2036 | Reducción progresiva anual de 25 sem (1.250 en 2026 a 1.000 en 2036) | `VERIFICADA` |
| `RULE-WEEK-CALENDAR-SL138` | Corte Suprema de Justicia, SL138-2024 | [Corte Suprema](https://cortesuprema.gov.co/semanas-de-cotizacion-a-pension-se-deben-contabilizar-con-dias-calendario-no-con-meses-de-30-dias/) | Vinculante | Días calendario reales (7 días = 1 sem), sin duplicidad patronal | `VERIFICADA` |
| `RULE-IBL-ORDINARY-L100-ART21` | Ley 100 de 1993, Art. 21 | [Normograma SENA](https://normograma.sena.edu.co/compilacion/docs/ley_0100_1993.htm) | 1994 en adelante | Actualización IPC. Toda la vida procede solo con $\ge 1.250$ sem si es superior | `VERIFICADA` |
| `RULE-IBL-EFFECTIVE-SL18546` | Corte Suprema de Justicia, SL18546-2016 | [Corte Suprema](https://www.cortesuprema.gov.co/corte/wp-content/uploads/relatorias/la/babr2017/SL18546-2016.pdf) | Vinculante | Últimos 10 años = 3.650 días de cotizaciones efectivas (no lagunas cero) | `VERIFICADA` |
| `RULE-REPLACEMENT-RATE-L797` | Ley 797 de 2003, Art. 10 | [Colpensiones](https://normativa.colpensiones.gov.co/compilacion/docs/ley_0797_2003.htm) | 2004 en adelante | $r = 65.5 - 0.5s$; +1.5% por cada 50 semanas adicionales | `VERIFICADA` |
| `RULE-NO-UNIVERSAL-1800-SL810` | Corte Suprema de Justicia, SL810-2023 | [Corte Suprema](https://www.cortesuprema.gov.co/corte/wp-content/uploads/relatorias/la/bjun2023/SL810-2023.pdf) | Vinculante | Semanas $> 1.800$ computan para alcanzar el tope del 80% | `VERIFICADA` |
| `RULE-MIN-MAX-PENSION-L100` | Ley 100 de 1993, Arts. 18, 34, 35 | [Colpensiones](https://normativa.colpensiones.gov.co/compilacion/docs/ley_0100_1993.htm) | Vigente | Mínimo 1 SMLMV; Máximo 25 SMLMV | `VERIFICADA` |
| `RULE-HEALTH-DISCOUNT-L2010` | Ley 2010 de 2019 / Ley 2294 de 2023 | [Colpensiones](https://www.colpensiones.gov.co/publicaciones/4994/) | 2024 en adelante | 1 SMLMV: 4%; >1 a 3 SMLMV: 10%; >3 SMLMV: 12% | `VERIFICADA` |
| `RULE-SOLIDARITY-FUND-D1833` | Decreto 1833 de 2016, Art. 2.2.14.1.38 | [Normativa Gov](https://normativa.colpensiones.gov.co/colpens/docs/decreto_1833_2016_pr021.htm) | Vigente | >10 a 20 SMLMV: 1%; >20 SMLMV: 2% (FSP Subsistencia) | `VERIFICADA` |
| `RULE-SPECIAL-REGIMES-SCOPE` | Ley 100 de 1993 / Dec. 2090 de 2003 | [Colpensiones](https://normativa.colpensiones.gov.co/compilacion/docs/ley_0100_1993.htm) | Vigente | Casos especiales catalogados como Fuera de Alcance del simulador ordinario | `VERIFICADA` |

---

## Reglas Pendientes de Validación Normativa

1. **Tratamiento Administrativo de Semanas por Hijos en Transición:**  
   La Sentencia C-054 de 2024 y la Ley 2381 contemplan beneficios de semanas por hijo. Sin embargo, en el régimen de transición ordinario estricto de la Ley 100, Colpensiones exige cumplimiento de semanas cotizadas efectivas para la causal ordinaria salvo reglamentación expresa del Gobierno Nacional. Por tanto, el simulador **no incorpora deducciones automáticas por hijos** sin validación reglamentaria específica.
2. **Semanas Cotizadas entre Julio de 2025 y Abril de 2027 para Afiliados con Déficit al Corte Anterior:**  
   Con el diferimiento de la vigencia ordenado por la Sentencia C-264 de 2026 al 1 de abril de 2027, las semanas causadas en dicho intervalo cuentan para el cómputo de las 750/900 semanas si se consolidan antes de la nueva fecha de entrada en vigor. Si a la fecha actual el corte es futuro, el simulador clasifica la situación como `EVALUACION_NO_DEFINITIVA_FECHA_CORTE_FUTURA`.
