"""Official DANE Historical Consumer Price Index (IPC) Series for Colombia.

Series: Serie de Empalme Base Diciembre 2018 = 100.
Entity: Departamento Administrativo Nacional de Estadística (DANE).
Source File: anex-IPC-Indices-ago2026.xlsx
Publication Date: 2026-09-07 (Actualizado el 7 de Septiembre de 2026).
Query Date: 2026-09-27.
File Hash (SHA-256): bd622e4c35b80c83085cbd24b6fdc282e578c0c2b15ac6f9eae332ddff52e264
Coverage: Total Nacional, 2003-01 a 2026-08 (284 observaciones oficiales mensuales).
"""

from decimal import Decimal
from typing import Any


class IPCFaltanteError(ValueError):
    """Raised when an official IPC observation is absent or cannot be verified."""

    def __init__(self, year: int, month: int, message: str) -> None:
        super().__init__(message)
        self.year = year
        self.month = month
        self.message = message


DANE_IPC_METADATA: dict[str, Any] = {
    "source": "DANE",
    "entity": "Departamento Administrativo Nacional de Estadística",
    "file": "anex-IPC-Indices-ago2026.xlsx",
    "publication_date": "2026-09-07",
    "query_date": "2026-09-27",
    "base": "Diciembre 2018 = 100.0",
    "coverage": "Total Nacional",
    "start_period": "2003-01",
    "end_period": "2026-08",
    "total_observations": 284,
    "sha256": "bd622e4c35b80c83085cbd24b6fdc282e578c0c2b15ac6f9eae332ddff52e264",
    "methodology": "Serie de Empalme oficial DANE (canasta 2018)",
}


def get_dane_ipc_metadata() -> dict[str, Any]:
    """Returns official DANE metadata and provenance of the loaded IPC series."""
    return dict(DANE_IPC_METADATA)


# Official DANE Spliced Series (Base Dec 2018 = 100.0)
# Format: (Year, Month): Decimal(IndexValue)
IPC_SERIES_BASE_2018: dict[tuple[int, int], Decimal] = {
    # 2003
    (2003, 1): Decimal("50.42"),
    (2003, 2): Decimal("50.98"),
    (2003, 3): Decimal("51.51"),
    (2003, 4): Decimal("52.10"),
    (2003, 5): Decimal("52.36"),
    (2003, 6): Decimal("52.33"),
    (2003, 7): Decimal("52.26"),
    (2003, 8): Decimal("52.42"),
    (2003, 9): Decimal("52.53"),
    (2003, 10): Decimal("52.56"),
    (2003, 11): Decimal("52.75"),
    (2003, 12): Decimal("53.07"),
    # 2004
    (2004, 1): Decimal("53.54"),
    (2004, 2): Decimal("54.18"),
    (2004, 3): Decimal("54.71"),
    (2004, 4): Decimal("54.96"),
    (2004, 5): Decimal("55.17"),
    (2004, 6): Decimal("55.51"),
    (2004, 7): Decimal("55.49"),
    (2004, 8): Decimal("55.51"),
    (2004, 9): Decimal("55.67"),
    (2004, 10): Decimal("55.66"),
    (2004, 11): Decimal("55.82"),
    (2004, 12): Decimal("55.99"),
    # 2005
    (2005, 1): Decimal("56.45"),
    (2005, 2): Decimal("57.02"),
    (2005, 3): Decimal("57.46"),
    (2005, 4): Decimal("57.72"),
    (2005, 5): Decimal("57.95"),
    (2005, 6): Decimal("58.18"),
    (2005, 7): Decimal("58.21"),
    (2005, 8): Decimal("58.21"),
    (2005, 9): Decimal("58.46"),
    (2005, 10): Decimal("58.60"),
    (2005, 11): Decimal("58.66"),
    (2005, 12): Decimal("58.70"),
    # 2006
    (2006, 1): Decimal("59.02"),
    (2006, 2): Decimal("59.41"),
    (2006, 3): Decimal("59.83"),
    (2006, 4): Decimal("60.09"),
    (2006, 5): Decimal("60.29"),
    (2006, 6): Decimal("60.48"),
    (2006, 7): Decimal("60.73"),
    (2006, 8): Decimal("60.96"),
    (2006, 9): Decimal("61.14"),
    (2006, 10): Decimal("61.05"),
    (2006, 11): Decimal("61.19"),
    (2006, 12): Decimal("61.33"),
    # 2007
    (2007, 1): Decimal("61.80"),
    (2007, 2): Decimal("62.53"),
    (2007, 3): Decimal("63.29"),
    (2007, 4): Decimal("63.85"),
    (2007, 5): Decimal("64.05"),
    (2007, 6): Decimal("64.12"),
    (2007, 7): Decimal("64.23"),
    (2007, 8): Decimal("64.14"),
    (2007, 9): Decimal("64.20"),
    (2007, 10): Decimal("64.20"),
    (2007, 11): Decimal("64.51"),
    (2007, 12): Decimal("64.82"),
    # 2008
    (2008, 1): Decimal("65.51"),
    (2008, 2): Decimal("66.50"),
    (2008, 3): Decimal("67.04"),
    (2008, 4): Decimal("67.51"),
    (2008, 5): Decimal("68.14"),
    (2008, 6): Decimal("68.73"),
    (2008, 7): Decimal("69.06"),
    (2008, 8): Decimal("69.19"),
    (2008, 9): Decimal("69.06"),
    (2008, 10): Decimal("69.30"),
    (2008, 11): Decimal("69.49"),
    (2008, 12): Decimal("69.80"),
    # 2009
    (2009, 1): Decimal("70.21"),
    (2009, 2): Decimal("70.80"),
    (2009, 3): Decimal("71.15"),
    (2009, 4): Decimal("71.38"),
    (2009, 5): Decimal("71.39"),
    (2009, 6): Decimal("71.35"),
    (2009, 7): Decimal("71.32"),
    (2009, 8): Decimal("71.35"),
    (2009, 9): Decimal("71.28"),
    (2009, 10): Decimal("71.19"),
    (2009, 11): Decimal("71.14"),
    (2009, 12): Decimal("71.20"),
    # 2010
    (2010, 1): Decimal("71.69"),
    (2010, 2): Decimal("72.28"),
    (2010, 3): Decimal("72.46"),
    (2010, 4): Decimal("72.79"),
    (2010, 5): Decimal("72.87"),
    (2010, 6): Decimal("72.95"),
    (2010, 7): Decimal("72.92"),
    (2010, 8): Decimal("73.00"),
    (2010, 9): Decimal("72.90"),
    (2010, 10): Decimal("72.84"),
    (2010, 11): Decimal("72.98"),
    (2010, 12): Decimal("73.45"),
    # 2011
    (2011, 1): Decimal("74.12"),
    (2011, 2): Decimal("74.57"),
    (2011, 3): Decimal("74.77"),
    (2011, 4): Decimal("74.86"),
    (2011, 5): Decimal("75.07"),
    (2011, 6): Decimal("75.31"),
    (2011, 7): Decimal("75.42"),
    (2011, 8): Decimal("75.39"),
    (2011, 9): Decimal("75.62"),
    (2011, 10): Decimal("75.77"),
    (2011, 11): Decimal("75.87"),
    (2011, 12): Decimal("76.19"),
    # 2012
    (2012, 1): Decimal("76.75"),
    (2012, 2): Decimal("77.22"),
    (2012, 3): Decimal("77.31"),
    (2012, 4): Decimal("77.42"),
    (2012, 5): Decimal("77.66"),
    (2012, 6): Decimal("77.72"),
    (2012, 7): Decimal("77.70"),
    (2012, 8): Decimal("77.73"),
    (2012, 9): Decimal("77.96"),
    (2012, 10): Decimal("78.08"),
    (2012, 11): Decimal("77.98"),
    (2012, 12): Decimal("78.05"),
    # 2013
    (2013, 1): Decimal("78.28"),
    (2013, 2): Decimal("78.63"),
    (2013, 3): Decimal("78.79"),
    (2013, 4): Decimal("78.99"),
    (2013, 5): Decimal("79.21"),
    (2013, 6): Decimal("79.39"),
    (2013, 7): Decimal("79.43"),
    (2013, 8): Decimal("79.50"),
    (2013, 9): Decimal("79.73"),
    (2013, 10): Decimal("79.52"),
    (2013, 11): Decimal("79.35"),
    (2013, 12): Decimal("79.56"),
    # 2014
    (2014, 1): Decimal("79.95"),
    (2014, 2): Decimal("80.45"),
    (2014, 3): Decimal("80.77"),
    (2014, 4): Decimal("81.14"),
    (2014, 5): Decimal("81.53"),
    (2014, 6): Decimal("81.61"),
    (2014, 7): Decimal("81.73"),
    (2014, 8): Decimal("81.90"),
    (2014, 9): Decimal("82.01"),
    (2014, 10): Decimal("82.14"),
    (2014, 11): Decimal("82.25"),
    (2014, 12): Decimal("82.47"),
    # 2015
    (2015, 1): Decimal("83.00"),
    (2015, 2): Decimal("83.96"),
    (2015, 3): Decimal("84.45"),
    (2015, 4): Decimal("84.90"),
    (2015, 5): Decimal("85.12"),
    (2015, 6): Decimal("85.21"),
    (2015, 7): Decimal("85.37"),
    (2015, 8): Decimal("85.78"),
    (2015, 9): Decimal("86.39"),
    (2015, 10): Decimal("86.98"),
    (2015, 11): Decimal("87.51"),
    (2015, 12): Decimal("88.05"),
    # 2016
    (2016, 1): Decimal("89.19"),
    (2016, 2): Decimal("90.33"),
    (2016, 3): Decimal("91.18"),
    (2016, 4): Decimal("91.63"),
    (2016, 5): Decimal("92.10"),
    (2016, 6): Decimal("92.54"),
    (2016, 7): Decimal("93.02"),
    (2016, 8): Decimal("92.73"),
    (2016, 9): Decimal("92.68"),
    (2016, 10): Decimal("92.62"),
    (2016, 11): Decimal("92.73"),
    (2016, 12): Decimal("93.11"),
    # 2017
    (2017, 1): Decimal("94.07"),
    (2017, 2): Decimal("95.01"),
    (2017, 3): Decimal("95.46"),
    (2017, 4): Decimal("95.91"),
    (2017, 5): Decimal("96.12"),
    (2017, 6): Decimal("96.23"),
    (2017, 7): Decimal("96.18"),
    (2017, 8): Decimal("96.32"),
    (2017, 9): Decimal("96.36"),
    (2017, 10): Decimal("96.37"),
    (2017, 11): Decimal("96.55"),
    (2017, 12): Decimal("96.92"),
    # 2018
    (2018, 1): Decimal("97.53"),
    (2018, 2): Decimal("98.22"),
    (2018, 3): Decimal("98.45"),
    (2018, 4): Decimal("98.91"),
    (2018, 5): Decimal("99.16"),
    (2018, 6): Decimal("99.31"),
    (2018, 7): Decimal("99.18"),
    (2018, 8): Decimal("99.30"),
    (2018, 9): Decimal("99.47"),
    (2018, 10): Decimal("99.59"),
    (2018, 11): Decimal("99.70"),
    (2018, 12): Decimal("100.00"),
    # 2019
    (2019, 1): Decimal("100.60"),
    (2019, 2): Decimal("101.18"),
    (2019, 3): Decimal("101.62"),
    (2019, 4): Decimal("102.12"),
    (2019, 5): Decimal("102.44"),
    (2019, 6): Decimal("102.71"),
    (2019, 7): Decimal("102.94"),
    (2019, 8): Decimal("103.03"),
    (2019, 9): Decimal("103.26"),
    (2019, 10): Decimal("103.43"),
    (2019, 11): Decimal("103.54"),
    (2019, 12): Decimal("103.80"),
    # 2020
    (2020, 1): Decimal("104.24"),
    (2020, 2): Decimal("104.94"),
    (2020, 3): Decimal("105.53"),
    (2020, 4): Decimal("105.70"),
    (2020, 5): Decimal("105.36"),
    (2020, 6): Decimal("104.97"),
    (2020, 7): Decimal("104.97"),
    (2020, 8): Decimal("104.96"),
    (2020, 9): Decimal("105.29"),
    (2020, 10): Decimal("105.23"),
    (2020, 11): Decimal("105.08"),
    (2020, 12): Decimal("105.48"),
    # 2021
    (2021, 1): Decimal("105.91"),
    (2021, 2): Decimal("106.58"),
    (2021, 3): Decimal("107.12"),
    (2021, 4): Decimal("107.76"),
    (2021, 5): Decimal("108.84"),
    (2021, 6): Decimal("108.78"),
    (2021, 7): Decimal("109.14"),
    (2021, 8): Decimal("109.62"),
    (2021, 9): Decimal("110.04"),
    (2021, 10): Decimal("110.06"),
    (2021, 11): Decimal("110.60"),
    (2021, 12): Decimal("111.41"),
    # 2022
    (2022, 1): Decimal("113.26"),
    (2022, 2): Decimal("115.11"),
    (2022, 3): Decimal("116.26"),
    (2022, 4): Decimal("117.71"),
    (2022, 5): Decimal("118.70"),
    (2022, 6): Decimal("119.31"),
    (2022, 7): Decimal("120.27"),
    (2022, 8): Decimal("121.50"),
    (2022, 9): Decimal("122.63"),
    (2022, 10): Decimal("123.51"),
    (2022, 11): Decimal("124.46"),
    (2022, 12): Decimal("126.03"),
    # 2023
    (2023, 1): Decimal("128.27"),
    (2023, 2): Decimal("130.40"),
    (2023, 3): Decimal("131.77"),
    (2023, 4): Decimal("132.80"),
    (2023, 5): Decimal("133.38"),
    (2023, 6): Decimal("133.78"),
    (2023, 7): Decimal("134.45"),
    (2023, 8): Decimal("135.39"),
    (2023, 9): Decimal("136.11"),
    (2023, 10): Decimal("136.45"),
    (2023, 11): Decimal("137.09"),
    (2023, 12): Decimal("137.72"),
    # 2024
    (2024, 1): Decimal("138.98"),
    (2024, 2): Decimal("140.49"),
    (2024, 3): Decimal("141.48"),
    (2024, 4): Decimal("142.32"),
    (2024, 5): Decimal("142.92"),
    (2024, 6): Decimal("143.38"),
    (2024, 7): Decimal("143.67"),
    (2024, 8): Decimal("143.67"),
    (2024, 9): Decimal("144.02"),
    (2024, 10): Decimal("143.83"),
    (2024, 11): Decimal("144.22"),
    (2024, 12): Decimal("144.88"),
    # 2025
    (2025, 1): Decimal("146.24"),
    (2025, 2): Decimal("147.90"),
    (2025, 3): Decimal("148.68"),
    (2025, 4): Decimal("149.66"),
    (2025, 5): Decimal("150.14"),
    (2025, 6): Decimal("150.30"),
    (2025, 7): Decimal("150.71"),
    (2025, 8): Decimal("150.99"),
    (2025, 9): Decimal("151.48"),
    (2025, 10): Decimal("151.76"),
    (2025, 11): Decimal("151.87"),
    (2025, 12): Decimal("152.27"),
    # 2026
    (2026, 1): Decimal("154.07"),
    (2026, 2): Decimal("155.73"),
    (2026, 3): Decimal("156.94"),
    (2026, 4): Decimal("158.17"),
    (2026, 5): Decimal("158.91"),
    (2026, 6): Decimal("159.53"),
    (2026, 7): Decimal("159.79"),
    (2026, 8): Decimal("160.42"),
}


def get_ipc(year: int, month: int) -> Decimal:
    """Returns the official DANE IPC index for a given year and month (Base Dec 2018 = 100).

    Raises:
        IPCFaltanteError: If the observation is not in the certified DANE series.
            Missing months are strictly NOT substituted by annual averages or linear guesses.
    """
    if (year, month) in IPC_SERIES_BASE_2018:
        return IPC_SERIES_BASE_2018[(year, month)]

    if year < 2003:
        raise IPCFaltanteError(
            year,
            month,
            f"IPC oficial no disponible para {year}-{month:02d}. "
            "La serie de empalme oficial DANE continua (Base Diciembre 2018=100) inicia en 2003-01. "
            "Para liquidar cotizaciones anteriores se requiere certificación oficial o valor indexado.",
        )

    if (year < 2026) or (year == 2026 and month <= 8):
        raise IPCFaltanteError(
            year,
            month,
            f"Dato mensual del IPC no disponible para {year}-{month:02d}. No se sustituye por promedios anuales.",
        )

    raise IPCFaltanteError(
        year,
        month,
        f"IPC observado no disponible para fecha futura {year}-{month:02d}. Requiere proyección con supuesto explícito de inflación.",
    )


def calculate_ipc_adjustment_factor(
    initial_year: int,
    initial_month: int,
    target_year: int,
    target_month: int,
    assumed_annual_inflation: Decimal = Decimal("0.04"),
) -> Decimal:
    """Calculates IPC multiplier: IPC_target / IPC_initial.

    If target date is beyond official observed series (August 2026),
    projects IPC using assumed_annual_inflation without double-counting.
    Historical missing months strictly raise IPCFaltanteError.
    """
    latest_obs_year, latest_obs_month = 2026, 8
    latest_obs_ipc = IPC_SERIES_BASE_2018[(latest_obs_year, latest_obs_month)]

    def _resolve_ipc(year: int, month: int) -> Decimal:
        if (year < latest_obs_year) or (
            year == latest_obs_year and month <= latest_obs_month
        ):
            return get_ipc(year, month)
        months_difference = (year - latest_obs_year) * 12 + (month - latest_obs_month)
        monthly_inflation_factor = (Decimal(1) + assumed_annual_inflation) ** (
            Decimal(months_difference) / Decimal(12)
        )
        return latest_obs_ipc * monthly_inflation_factor

    ipc_initial = _resolve_ipc(initial_year, initial_month)
    ipc_target = _resolve_ipc(target_year, target_month)

    return ipc_target / ipc_initial
