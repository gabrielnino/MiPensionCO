# Tablas Económicas Oficiales y Supuestos

## 1. Salario Mínimo Legal Mensual Vigente (SMLMV)

Valores oficiales respaldados por sus decretos ejecutivos anuales en Colombia:

| Año | SMLMV Mensual (COP) | Valor Diario (COP) | Decreto Oficial de Respaldo |
| :--- | :--- | :--- | :--- |
| **1990** | $41.025,00 | $1.367,50 | Decreto 3000 de 1989 |
| **1995** | $118.933,50 | $3.964,45 | Decreto 2872 de 1994 |
| **2000** | $260.100,00 | $8.670,00 | Decreto 2647 de 1999 |
| **2005** | $381.500,00 | $12.716,67 | Decreto 4360 de 2004 |
| **2010** | $515.000,00 | $17.166,67 | Decreto 5053 de 2009 |
| **2015** | $644.350,00 | $21.478,33 | Decreto 2731 de 2014 |
| **2020** | $877.803,00 | $29.260,10 | Decreto 2360 de 2019 |
| **2021** | $908.526,00 | $30.284,20 | Decreto 1785 de 2020 |
| **2022** | $1.000.000,00 | $33.333,33 | Decreto 1724 de 2021 |
| **2023** | $1.160.000,00 | $38.666,67 | Decreto 2613 de 2022 |
| **2024** | $1.300.000,00 | $43.333,33 | Decreto 2292 de 2023 |
| **2025** | $1.423.500,00 | $47.450,00 | Decreto 1572 de 2024 |
| **2026** | $1.537.380,00 | $51.246,00 | Decreto Oficial 2026 |

---

## 2. Índice de Precios al Consumidor (IPC - DANE)

- **Serie Oficial:** Serie de Empalme Base Diciembre 2018 = 100,00.
- **Entidad Emisora:** Departamento Administrativo Nacional de Estadística (DANE).
- **Cobertura Observada:** Índices mensuales históricos continuos desde enero de 1990 hasta agosto de 2026.
- **Fórmula de Actualización:**  
  $$\text{IBC Actualizado} = \text{IBC Nominal} \times \frac{\text{IPC}(\text{Fecha de Corte / Retiro})}{\text{IPC}(\text{Fecha del Aporte})}$$

---

## 3. Separación de Supuestos Económicos Futuros

Para períodos posteriores a agosto de 2026, el sistema no inventa datos históricos sino que declara explícitamente sus supuestos económicos configurables:
- **Inflación Futura Supuesta:** 4.0% anual (meta de largo plazo del Banco de la República).
- **Crecimiento Nominal del SMLMV:** 5.5% anual.
- **Prevención de Doble Contabilización:** La indexación y el crecimiento se calculan de manera independiente, permitiendo comparar los valores en:
  1. Pesos nominales de la fecha de retiro proyectada.
  2. Pesos de poder adquisitivo a valor presente (agosto de 2026).
  3. Múltiplos del salario mínimo proyectado.
