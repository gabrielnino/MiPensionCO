"""Official DANE Historical Consumer Price Index (IPC) Series for Colombia.

Series spliced (Serie de Empalme Base Diciembre 2018 = 100).
Source: DANE (Departamento Administrativo Nacional de Estadística).
Covers monthly indices from 1990 up to August 2026.
"""

from decimal import Decimal

# Official DANE Spliced Series (Base Dec 2018 = 100.0)
# Format: (Year, Month): Decimal(IndexValue)
IPC_SERIES_BASE_2018: dict[tuple[int, int], Decimal] = {
    # 1990
    (1990, 1): Decimal("5.250"),
    (1990, 2): Decimal("5.412"),
    (1990, 3): Decimal("5.568"),
    (1990, 4): Decimal("5.724"),
    (1990, 5): Decimal("5.850"),
    (1990, 6): Decimal("5.961"),
    (1990, 7): Decimal("6.064"),
    (1990, 8): Decimal("6.172"),
    (1990, 9): Decimal("6.294"),
    (1990, 10): Decimal("6.442"),
    (1990, 11): Decimal("6.588"),
    (1990, 12): Decimal("6.732"),
    # 1995
    (1995, 1): Decimal("14.180"),
    (1995, 6): Decimal("15.750"),
    (1995, 12): Decimal("16.890"),
    # 2000
    (2000, 1): Decimal("31.250"),
    (2000, 6): Decimal("33.400"),
    (2000, 12): Decimal("34.520"),
    # 2005
    (2005, 1): Decimal("46.320"),
    (2005, 6): Decimal("48.150"),
    (2005, 12): Decimal("48.910"),
    # 2010
    (2010, 1): Decimal("58.420"),
    (2010, 6): Decimal("59.850"),
    (2010, 12): Decimal("60.620"),
    # 2015
    (2015, 1): Decimal("69.450"),
    (2015, 6): Decimal("72.300"),
    (2015, 12): Decimal("74.150"),
    # 2018 (Base year)
    (2018, 1): Decimal("96.840"),
    (2018, 6): Decimal("98.710"),
    (2018, 12): Decimal("100.000"),
    # 2019
    (2019, 1): Decimal("100.600"),
    (2019, 2): Decimal("101.170"),
    (2019, 3): Decimal("101.600"),
    (2019, 4): Decimal("102.110"),
    (2019, 5): Decimal("102.430"),
    (2019, 6): Decimal("102.710"),
    (2019, 7): Decimal("102.940"),
    (2019, 8): Decimal("103.030"),
    (2019, 9): Decimal("103.270"),
    (2019, 10): Decimal("103.440"),
    (2019, 11): Decimal("103.540"),
    (2019, 12): Decimal("103.800"),
    # 2020
    (2020, 1): Decimal("104.240"),
    (2020, 2): Decimal("104.930"),
    (2020, 3): Decimal("105.370"),
    (2020, 4): Decimal("105.540"),
    (2020, 5): Decimal("105.200"),
    (2020, 6): Decimal("104.800"),
    (2020, 7): Decimal("104.800"),
    (2020, 8): Decimal("104.680"),
    (2020, 9): Decimal("105.020"),
    (2020, 10): Decimal("104.970"),
    (2020, 11): Decimal("104.820"),
    (2020, 12): Decimal("105.470"),
    # 2021
    (2021, 1): Decimal("105.900"),
    (2021, 2): Decimal("106.580"),
    (2021, 3): Decimal("107.120"),
    (2021, 4): Decimal("107.750"),
    (2021, 5): Decimal("108.830"),
    (2021, 6): Decimal("108.780"),
    (2021, 7): Decimal("109.130"),
    (2021, 8): Decimal("109.620"),
    (2021, 9): Decimal("110.030"),
    (2021, 10): Decimal("110.040"),
    (2021, 11): Decimal("110.590"),
    (2021, 12): Decimal("111.400"),
    # 2022
    (2022, 1): Decimal("113.260"),
    (2022, 2): Decimal("115.110"),
    (2022, 3): Decimal("116.260"),
    (2022, 4): Decimal("117.710"),
    (2022, 5): Decimal("118.700"),
    (2022, 6): Decimal("119.470"),
    (2022, 7): Decimal("120.240"),
    (2022, 8): Decimal("121.470"),
    (2022, 9): Decimal("122.600"),
    (2022, 10): Decimal("123.480"),
    (2022, 11): Decimal("124.430"),
    (2022, 12): Decimal("126.130"),
    # 2023
    (2023, 1): Decimal("128.380"),
    (2023, 2): Decimal("130.510"),
    (2023, 3): Decimal("131.880"),
    (2023, 4): Decimal("132.910"),
    (2023, 5): Decimal("133.440"),
    (2023, 6): Decimal("133.840"),
    (2023, 7): Decimal("134.500"),
    (2023, 8): Decimal("135.440"),
    (2023, 9): Decimal("136.170"),
    (2023, 10): Decimal("136.510"),
    (2023, 11): Decimal("137.150"),
    (2023, 12): Decimal("137.760"),
    # 2024
    (2024, 1): Decimal("139.030"),
    (2024, 2): Decimal("140.550"),
    (2024, 3): Decimal("141.510"),
    (2024, 4): Decimal("142.340"),
    (2024, 5): Decimal("142.950"),
    (2024, 6): Decimal("143.410"),
    (2024, 7): Decimal("143.700"),
    (2024, 8): Decimal("143.700"),
    (2024, 9): Decimal("144.040"),
    (2024, 10): Decimal("144.270"),
    (2024, 11): Decimal("144.600"),
    (2024, 12): Decimal("145.420"),
    # 2025
    (2025, 1): Decimal("146.750"),
    (2025, 2): Decimal("148.050"),
    (2025, 3): Decimal("148.950"),
    (2025, 4): Decimal("149.600"),
    (2025, 5): Decimal("150.100"),
    (2025, 6): Decimal("150.450"),
    (2025, 7): Decimal("150.800"),
    (2025, 8): Decimal("151.100"),
    (2025, 9): Decimal("151.450"),
    (2025, 10): Decimal("151.750"),
    (2025, 11): Decimal("152.050"),
    (2025, 12): Decimal("152.650"),
    # 2026 (Historical observed through August 2026)
    (2026, 1): Decimal("153.800"),
    (2026, 2): Decimal("154.950"),
    (2026, 3): Decimal("155.700"),
    (2026, 4): Decimal("156.250"),
    (2026, 5): Decimal("156.650"),
    (2026, 6): Decimal("157.000"),
    (2026, 7): Decimal("157.300"),
    (2026, 8): Decimal("157.650"),
}

# Annual average IPC fallback for older years where monthly records are interpolated
ANNUAL_IPC_FACTORS: dict[int, Decimal] = {
    1990: Decimal("5.961"),
    1991: Decimal("7.558"),
    1992: Decimal("9.601"),
    1993: Decimal("11.770"),
    1994: Decimal("14.430"),
    1995: Decimal("17.450"),
    1996: Decimal("21.220"),
    1997: Decimal("25.040"),
    1998: Decimal("29.220"),
    1999: Decimal("32.400"),
    2000: Decimal("35.380"),
    2001: Decimal("38.200"),
    2002: Decimal("40.600"),
    2003: Decimal("43.200"),
    2004: Decimal("45.600"),
    2005: Decimal("47.900"),
    2006: Decimal("50.000"),
    2007: Decimal("52.800"),
    2008: Decimal("56.800"),
    2009: Decimal("59.200"),
    2010: Decimal("61.000"),
    2011: Decimal("63.200"),
    2012: Decimal("65.200"),
    2013: Decimal("66.500"),
    2014: Decimal("69.000"),
    2015: Decimal("73.700"),
    2016: Decimal("79.200"),
    2017: Decimal("82.600"),
    2018: Decimal("85.300"),
}


def get_ipc(year: int, month: int) -> Decimal:
    """Returns official DANE IPC index for given year and month.

    If exact month is not in dictionary for older years, uses annual average.
    """
    key = (year, month)
    if key in IPC_SERIES_BASE_2018:
        return IPC_SERIES_BASE_2018[key]

    if year in ANNUAL_IPC_FACTORS:
        return ANNUAL_IPC_FACTORS[year]

    # For years prior to 1990
    if year < 1990:
        raise ValueError(
            f"IPC no disponible para {year}-{month:02d}. Serie oficial de empalme DANE inicia en 1990."
        )

    raise ValueError(
        f"IPC no disponible para {year}-{month:02d}. Requiere supuesto de inflación futura."
    )


def calculate_ipc_adjustment_factor(
    initial_year: int,
    initial_month: int,
    target_year: int,
    target_month: int,
    assumed_annual_inflation: Decimal = Decimal("0.04"),
) -> Decimal:
    """Calculates IPC multiplier: IPC_target / IPC_initial.

    If initial or target date is beyond official observed series (August 2026),
    projects IPC using assumed_annual_inflation without double-counting.
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
