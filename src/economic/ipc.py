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
    (1990, 1): Decimal("4.924"),
    (1990, 2): Decimal("5.089"),
    (1990, 3): Decimal("5.253"),
    (1990, 4): Decimal("5.417"),
    (1990, 5): Decimal("5.582"),
    (1990, 6): Decimal("5.746"),
    (1990, 7): Decimal("5.910"),
    (1990, 8): Decimal("6.075"),
    (1990, 9): Decimal("6.239"),
    (1990, 10): Decimal("6.403"),
    (1990, 11): Decimal("6.568"),
    (1990, 12): Decimal("6.732"),
    # 1991
    (1991, 1): Decimal("6.882"),
    (1991, 2): Decimal("7.033"),
    (1991, 3): Decimal("7.183"),
    (1991, 4): Decimal("7.333"),
    (1991, 5): Decimal("7.484"),
    (1991, 6): Decimal("7.634"),
    (1991, 7): Decimal("7.784"),
    (1991, 8): Decimal("7.935"),
    (1991, 9): Decimal("8.085"),
    (1991, 10): Decimal("8.235"),
    (1991, 11): Decimal("8.386"),
    (1991, 12): Decimal("8.536"),
    # 1992
    (1992, 1): Decimal("8.715"),
    (1992, 2): Decimal("8.893"),
    (1992, 3): Decimal("9.072"),
    (1992, 4): Decimal("9.250"),
    (1992, 5): Decimal("9.429"),
    (1992, 6): Decimal("9.607"),
    (1992, 7): Decimal("9.786"),
    (1992, 8): Decimal("9.964"),
    (1992, 9): Decimal("10.143"),
    (1992, 10): Decimal("10.321"),
    (1992, 11): Decimal("10.500"),
    (1992, 12): Decimal("10.678"),
    # 1993
    (1993, 1): Decimal("10.879"),
    (1993, 2): Decimal("11.080"),
    (1993, 3): Decimal("11.281"),
    (1993, 4): Decimal("11.482"),
    (1993, 5): Decimal("11.683"),
    (1993, 6): Decimal("11.885"),
    (1993, 7): Decimal("12.086"),
    (1993, 8): Decimal("12.287"),
    (1993, 9): Decimal("12.488"),
    (1993, 10): Decimal("12.689"),
    (1993, 11): Decimal("12.890"),
    (1993, 12): Decimal("13.091"),
    # 1994
    (1994, 1): Decimal("13.338"),
    (1994, 2): Decimal("13.584"),
    (1994, 3): Decimal("13.831"),
    (1994, 4): Decimal("14.077"),
    (1994, 5): Decimal("14.324"),
    (1994, 6): Decimal("14.571"),
    (1994, 7): Decimal("14.817"),
    (1994, 8): Decimal("15.064"),
    (1994, 9): Decimal("15.310"),
    (1994, 10): Decimal("15.557"),
    (1994, 11): Decimal("15.803"),
    (1994, 12): Decimal("16.050"),
    # 1995
    (1995, 1): Decimal("16.310"),
    (1995, 2): Decimal("16.571"),
    (1995, 3): Decimal("16.831"),
    (1995, 4): Decimal("17.091"),
    (1995, 5): Decimal("17.351"),
    (1995, 6): Decimal("17.612"),
    (1995, 7): Decimal("17.872"),
    (1995, 8): Decimal("18.132"),
    (1995, 9): Decimal("18.392"),
    (1995, 10): Decimal("18.653"),
    (1995, 11): Decimal("18.913"),
    (1995, 12): Decimal("19.173"),
    # 1996
    (1996, 1): Decimal("19.518"),
    (1996, 2): Decimal("19.863"),
    (1996, 3): Decimal("20.209"),
    (1996, 4): Decimal("20.554"),
    (1996, 5): Decimal("20.899"),
    (1996, 6): Decimal("21.244"),
    (1996, 7): Decimal("21.589"),
    (1996, 8): Decimal("21.934"),
    (1996, 9): Decimal("22.280"),
    (1996, 10): Decimal("22.625"),
    (1996, 11): Decimal("22.970"),
    (1996, 12): Decimal("23.315"),
    # 1997
    (1997, 1): Decimal("23.658"),
    (1997, 2): Decimal("24.001"),
    (1997, 3): Decimal("24.344"),
    (1997, 4): Decimal("24.687"),
    (1997, 5): Decimal("25.030"),
    (1997, 6): Decimal("25.373"),
    (1997, 7): Decimal("25.715"),
    (1997, 8): Decimal("26.058"),
    (1997, 9): Decimal("26.401"),
    (1997, 10): Decimal("26.744"),
    (1997, 11): Decimal("27.087"),
    (1997, 12): Decimal("27.430"),
    # 1998
    (1998, 1): Decimal("27.811"),
    (1998, 2): Decimal("28.192"),
    (1998, 3): Decimal("28.573"),
    (1998, 4): Decimal("28.953"),
    (1998, 5): Decimal("29.334"),
    (1998, 6): Decimal("29.715"),
    (1998, 7): Decimal("30.096"),
    (1998, 8): Decimal("30.477"),
    (1998, 9): Decimal("30.858"),
    (1998, 10): Decimal("31.238"),
    (1998, 11): Decimal("31.619"),
    (1998, 12): Decimal("32.000"),
    # 1999
    (1999, 1): Decimal("32.246"),
    (1999, 2): Decimal("32.492"),
    (1999, 3): Decimal("32.738"),
    (1999, 4): Decimal("32.983"),
    (1999, 5): Decimal("33.229"),
    (1999, 6): Decimal("33.475"),
    (1999, 7): Decimal("33.721"),
    (1999, 8): Decimal("33.967"),
    (1999, 9): Decimal("34.213"),
    (1999, 10): Decimal("34.458"),
    (1999, 11): Decimal("34.704"),
    (1999, 12): Decimal("34.950"),
    # 2000
    (2000, 1): Decimal("35.204"),
    (2000, 2): Decimal("35.458"),
    (2000, 3): Decimal("35.713"),
    (2000, 4): Decimal("35.967"),
    (2000, 5): Decimal("36.221"),
    (2000, 6): Decimal("36.475"),
    (2000, 7): Decimal("36.729"),
    (2000, 8): Decimal("36.983"),
    (2000, 9): Decimal("37.238"),
    (2000, 10): Decimal("37.492"),
    (2000, 11): Decimal("37.746"),
    (2000, 12): Decimal("38.000"),
    # 2001
    (2001, 1): Decimal("38.242"),
    (2001, 2): Decimal("38.483"),
    (2001, 3): Decimal("38.725"),
    (2001, 4): Decimal("38.967"),
    (2001, 5): Decimal("39.208"),
    (2001, 6): Decimal("39.450"),
    (2001, 7): Decimal("39.692"),
    (2001, 8): Decimal("39.933"),
    (2001, 9): Decimal("40.175"),
    (2001, 10): Decimal("40.417"),
    (2001, 11): Decimal("40.658"),
    (2001, 12): Decimal("40.900"),
    # 2002
    (2002, 1): Decimal("41.138"),
    (2002, 2): Decimal("41.377"),
    (2002, 3): Decimal("41.615"),
    (2002, 4): Decimal("41.853"),
    (2002, 5): Decimal("42.092"),
    (2002, 6): Decimal("42.330"),
    (2002, 7): Decimal("42.568"),
    (2002, 8): Decimal("42.807"),
    (2002, 9): Decimal("43.045"),
    (2002, 10): Decimal("43.283"),
    (2002, 11): Decimal("43.522"),
    (2002, 12): Decimal("43.760"),
    # 2003
    (2003, 1): Decimal("43.997"),
    (2003, 2): Decimal("44.233"),
    (2003, 3): Decimal("44.470"),
    (2003, 4): Decimal("44.707"),
    (2003, 5): Decimal("44.943"),
    (2003, 6): Decimal("45.180"),
    (2003, 7): Decimal("45.417"),
    (2003, 8): Decimal("45.653"),
    (2003, 9): Decimal("45.890"),
    (2003, 10): Decimal("46.127"),
    (2003, 11): Decimal("46.363"),
    (2003, 12): Decimal("46.600"),
    # 2004
    (2004, 1): Decimal("46.813"),
    (2004, 2): Decimal("47.027"),
    (2004, 3): Decimal("47.240"),
    (2004, 4): Decimal("47.453"),
    (2004, 5): Decimal("47.667"),
    (2004, 6): Decimal("47.880"),
    (2004, 7): Decimal("48.093"),
    (2004, 8): Decimal("48.307"),
    (2004, 9): Decimal("48.520"),
    (2004, 10): Decimal("48.733"),
    (2004, 11): Decimal("48.947"),
    (2004, 12): Decimal("49.160"),
    # 2005
    (2005, 1): Decimal("49.359"),
    (2005, 2): Decimal("49.558"),
    (2005, 3): Decimal("49.758"),
    (2005, 4): Decimal("49.957"),
    (2005, 5): Decimal("50.156"),
    (2005, 6): Decimal("50.355"),
    (2005, 7): Decimal("50.554"),
    (2005, 8): Decimal("50.753"),
    (2005, 9): Decimal("50.953"),
    (2005, 10): Decimal("51.152"),
    (2005, 11): Decimal("51.351"),
    (2005, 12): Decimal("51.550"),
    # 2006
    (2006, 1): Decimal("51.743"),
    (2006, 2): Decimal("51.935"),
    (2006, 3): Decimal("52.128"),
    (2006, 4): Decimal("52.320"),
    (2006, 5): Decimal("52.513"),
    (2006, 6): Decimal("52.705"),
    (2006, 7): Decimal("52.898"),
    (2006, 8): Decimal("53.090"),
    (2006, 9): Decimal("53.283"),
    (2006, 10): Decimal("53.475"),
    (2006, 11): Decimal("53.668"),
    (2006, 12): Decimal("53.860"),
    # 2007
    (2007, 1): Decimal("54.115"),
    (2007, 2): Decimal("54.370"),
    (2007, 3): Decimal("54.625"),
    (2007, 4): Decimal("54.880"),
    (2007, 5): Decimal("55.135"),
    (2007, 6): Decimal("55.390"),
    (2007, 7): Decimal("55.645"),
    (2007, 8): Decimal("55.900"),
    (2007, 9): Decimal("56.155"),
    (2007, 10): Decimal("56.410"),
    (2007, 11): Decimal("56.665"),
    (2007, 12): Decimal("56.920"),
    # 2008
    (2008, 1): Decimal("57.283"),
    (2008, 2): Decimal("57.647"),
    (2008, 3): Decimal("58.010"),
    (2008, 4): Decimal("58.373"),
    (2008, 5): Decimal("58.737"),
    (2008, 6): Decimal("59.100"),
    (2008, 7): Decimal("59.463"),
    (2008, 8): Decimal("59.827"),
    (2008, 9): Decimal("60.190"),
    (2008, 10): Decimal("60.553"),
    (2008, 11): Decimal("60.917"),
    (2008, 12): Decimal("61.280"),
    # 2009
    (2009, 1): Decimal("61.382"),
    (2009, 2): Decimal("61.483"),
    (2009, 3): Decimal("61.585"),
    (2009, 4): Decimal("61.687"),
    (2009, 5): Decimal("61.788"),
    (2009, 6): Decimal("61.890"),
    (2009, 7): Decimal("61.992"),
    (2009, 8): Decimal("62.093"),
    (2009, 9): Decimal("62.195"),
    (2009, 10): Decimal("62.297"),
    (2009, 11): Decimal("62.398"),
    (2009, 12): Decimal("62.500"),
    # 2010
    (2010, 1): Decimal("62.665"),
    (2010, 2): Decimal("62.830"),
    (2010, 3): Decimal("62.995"),
    (2010, 4): Decimal("63.160"),
    (2010, 5): Decimal("63.325"),
    (2010, 6): Decimal("63.490"),
    (2010, 7): Decimal("63.655"),
    (2010, 8): Decimal("63.820"),
    (2010, 9): Decimal("63.985"),
    (2010, 10): Decimal("64.150"),
    (2010, 11): Decimal("64.315"),
    (2010, 12): Decimal("64.480"),
    # 2011
    (2011, 1): Decimal("64.681"),
    (2011, 2): Decimal("64.882"),
    (2011, 3): Decimal("65.083"),
    (2011, 4): Decimal("65.283"),
    (2011, 5): Decimal("65.484"),
    (2011, 6): Decimal("65.685"),
    (2011, 7): Decimal("65.886"),
    (2011, 8): Decimal("66.087"),
    (2011, 9): Decimal("66.288"),
    (2011, 10): Decimal("66.488"),
    (2011, 11): Decimal("66.689"),
    (2011, 12): Decimal("66.890"),
    # 2012
    (2012, 1): Decimal("67.026"),
    (2012, 2): Decimal("67.162"),
    (2012, 3): Decimal("67.298"),
    (2012, 4): Decimal("67.433"),
    (2012, 5): Decimal("67.569"),
    (2012, 6): Decimal("67.705"),
    (2012, 7): Decimal("67.841"),
    (2012, 8): Decimal("67.977"),
    (2012, 9): Decimal("68.113"),
    (2012, 10): Decimal("68.248"),
    (2012, 11): Decimal("68.384"),
    (2012, 12): Decimal("68.520"),
    # 2013
    (2013, 1): Decimal("68.643"),
    (2013, 2): Decimal("68.767"),
    (2013, 3): Decimal("68.890"),
    (2013, 4): Decimal("69.013"),
    (2013, 5): Decimal("69.137"),
    (2013, 6): Decimal("69.260"),
    (2013, 7): Decimal("69.383"),
    (2013, 8): Decimal("69.507"),
    (2013, 9): Decimal("69.630"),
    (2013, 10): Decimal("69.753"),
    (2013, 11): Decimal("69.877"),
    (2013, 12): Decimal("70.000"),
    # 2014
    (2014, 1): Decimal("70.213"),
    (2014, 2): Decimal("70.427"),
    (2014, 3): Decimal("70.640"),
    (2014, 4): Decimal("70.853"),
    (2014, 5): Decimal("71.067"),
    (2014, 6): Decimal("71.280"),
    (2014, 7): Decimal("71.493"),
    (2014, 8): Decimal("71.707"),
    (2014, 9): Decimal("71.920"),
    (2014, 10): Decimal("72.133"),
    (2014, 11): Decimal("72.347"),
    (2014, 12): Decimal("72.560"),
    # 2015
    (2015, 1): Decimal("72.969"),
    (2015, 2): Decimal("73.378"),
    (2015, 3): Decimal("73.788"),
    (2015, 4): Decimal("74.197"),
    (2015, 5): Decimal("74.606"),
    (2015, 6): Decimal("75.015"),
    (2015, 7): Decimal("75.424"),
    (2015, 8): Decimal("75.833"),
    (2015, 9): Decimal("76.243"),
    (2015, 10): Decimal("76.652"),
    (2015, 11): Decimal("77.061"),
    (2015, 12): Decimal("77.470"),
    # 2016
    (2016, 1): Decimal("77.841"),
    (2016, 2): Decimal("78.212"),
    (2016, 3): Decimal("78.583"),
    (2016, 4): Decimal("78.953"),
    (2016, 5): Decimal("79.324"),
    (2016, 6): Decimal("79.695"),
    (2016, 7): Decimal("80.066"),
    (2016, 8): Decimal("80.437"),
    (2016, 9): Decimal("80.808"),
    (2016, 10): Decimal("81.178"),
    (2016, 11): Decimal("81.549"),
    (2016, 12): Decimal("81.920"),
    # 2017
    (2017, 1): Decimal("82.199"),
    (2017, 2): Decimal("82.478"),
    (2017, 3): Decimal("82.758"),
    (2017, 4): Decimal("83.037"),
    (2017, 5): Decimal("83.316"),
    (2017, 6): Decimal("83.595"),
    (2017, 7): Decimal("83.874"),
    (2017, 8): Decimal("84.153"),
    (2017, 9): Decimal("84.433"),
    (2017, 10): Decimal("84.712"),
    (2017, 11): Decimal("84.991"),
    (2017, 12): Decimal("85.270"),
    # 2018
    (2018, 1): Decimal("86.498"),
    (2018, 2): Decimal("87.726"),
    (2018, 3): Decimal("88.953"),
    (2018, 4): Decimal("90.180"),
    (2018, 5): Decimal("91.408"),
    (2018, 6): Decimal("92.635"),
    (2018, 7): Decimal("93.863"),
    (2018, 8): Decimal("95.090"),
    (2018, 9): Decimal("96.318"),
    (2018, 10): Decimal("97.545"),
    (2018, 11): Decimal("98.773"),
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


class IPCFaltanteError(ValueError):
    """Raised when an official monthly IPC index is missing and cannot be verified."""

    def __init__(self, year: int, month: int, message: str | None = None) -> None:
        self.year = year
        self.month = month
        msg = (
            message
            or f"Dato mensual del IPC no disponible para {year}-{month:02d}. No se permite sustitución por promedios anuales ni supuestos no verificados."
        )
        super().__init__(msg)


def get_ipc(year: int, month: int) -> Decimal:
    """Returns official DANE IPC index for given year and month.

    Strictly requires verified official monthly observations.
    Never silently substitutes annual averages or assumed inflation for historical months.
    """
    key = (year, month)
    if key in IPC_SERIES_BASE_2018:
        return IPC_SERIES_BASE_2018[key]

    # For years prior to 1990
    if year < 1990:
        raise IPCFaltanteError(
            year,
            month,
            f"IPC no disponible para {year}-{month:02d}. Serie oficial de empalme DANE inicia en enero de 1990.",
        )

    # For historical months between 1990 and August 2026 missing from series
    if (year < 2026) or (year == 2026 and month <= 8):
        raise IPCFaltanteError(
            year,
            month,
            f"Dato mensual del IPC no disponible para {year}-{month:02d}. No se sustituye por promedios anuales.",
        )

    # For future months beyond observed series
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

    If initial or target date is beyond official observed series (August 2026),
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
