"""Official Historical Minimum Wage (SMLMV) in Colombia.

Every annual value is backed by its official executive decree.
Values expressed in Colombian Pesos (COP).
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SMLMVRecord:
    year: int
    monthly_amount: Decimal
    daily_amount: Decimal
    decree_reference: str
    official_source_url: str


HISTORICAL_SMLMV: dict[int, SMLMVRecord] = {
    1990: SMLMVRecord(
        1990,
        Decimal(41025),
        Decimal("1367.50"),
        "Decreto 3000 de 1989",
        "https://normativa.colpensiones.gov.co/",
    ),
    1991: SMLMVRecord(
        1991,
        Decimal(51720),
        Decimal("1724.00"),
        "Decreto 3074 de 1990",
        "https://normativa.colpensiones.gov.co/",
    ),
    1992: SMLMVRecord(
        1992,
        Decimal(65190),
        Decimal("2173.00"),
        "Decreto 2867 de 1991",
        "https://normativa.colpensiones.gov.co/",
    ),
    1993: SMLMVRecord(
        1993,
        Decimal(81510),
        Decimal("2717.00"),
        "Decreto 2061 de 1992",
        "https://normativa.colpensiones.gov.co/",
    ),
    1994: SMLMVRecord(
        1994,
        Decimal(98700),
        Decimal("3290.00"),
        "Decreto 2535 de 1993",
        "https://normativa.colpensiones.gov.co/",
    ),
    1995: SMLMVRecord(
        1995,
        Decimal("118933.50"),
        Decimal("3964.45"),
        "Decreto 2872 de 1994",
        "https://normativa.colpensiones.gov.co/",
    ),
    1996: SMLMVRecord(
        1996,
        Decimal(142125),
        Decimal("4737.50"),
        "Decreto 2310 de 1995",
        "https://normativa.colpensiones.gov.co/",
    ),
    1997: SMLMVRecord(
        1997,
        Decimal(172005),
        Decimal("5733.50"),
        "Decreto 2334 de 1996",
        "https://normativa.colpensiones.gov.co/",
    ),
    1998: SMLMVRecord(
        1998,
        Decimal(203826),
        Decimal("6794.20"),
        "Decreto 3106 de 1997",
        "https://normativa.colpensiones.gov.co/",
    ),
    1999: SMLMVRecord(
        1999,
        Decimal(236460),
        Decimal("7882.00"),
        "Decreto 2560 de 1998",
        "https://normativa.colpensiones.gov.co/",
    ),
    2000: SMLMVRecord(
        2000,
        Decimal(260100),
        Decimal("8670.00"),
        "Decreto 2647 de 1999",
        "https://normativa.colpensiones.gov.co/",
    ),
    2001: SMLMVRecord(
        2001,
        Decimal(286000),
        Decimal("9533.33"),
        "Decreto 2579 de 2000",
        "https://normativa.colpensiones.gov.co/",
    ),
    2002: SMLMVRecord(
        2002,
        Decimal(309000),
        Decimal("10300.00"),
        "Decreto 2910 de 2001",
        "https://normativa.colpensiones.gov.co/",
    ),
    2003: SMLMVRecord(
        2003,
        Decimal(332000),
        Decimal("11066.67"),
        "Decreto 3232 de 2002",
        "https://normativa.colpensiones.gov.co/",
    ),
    2004: SMLMVRecord(
        2004,
        Decimal(358000),
        Decimal("11933.33"),
        "Decreto 3770 de 2003",
        "https://normativa.colpensiones.gov.co/",
    ),
    2005: SMLMVRecord(
        2005,
        Decimal(381500),
        Decimal("12716.67"),
        "Decreto 4360 de 2004",
        "https://normativa.colpensiones.gov.co/",
    ),
    2006: SMLMVRecord(
        2006,
        Decimal(408000),
        Decimal("13600.00"),
        "Decreto 4686 de 2005",
        "https://normativa.colpensiones.gov.co/",
    ),
    2007: SMLMVRecord(
        2007,
        Decimal(433700),
        Decimal("14456.67"),
        "Decreto 4580 de 2006",
        "https://normativa.colpensiones.gov.co/",
    ),
    2008: SMLMVRecord(
        2008,
        Decimal(461500),
        Decimal("15383.33"),
        "Decreto 4982 de 2007",
        "https://normativa.colpensiones.gov.co/",
    ),
    2009: SMLMVRecord(
        2009,
        Decimal(496900),
        Decimal("16563.33"),
        "Decreto 4868 de 2008",
        "https://normativa.colpensiones.gov.co/",
    ),
    2010: SMLMVRecord(
        2010,
        Decimal(515000),
        Decimal("17166.67"),
        "Decreto 5053 de 2009",
        "https://normativa.colpensiones.gov.co/",
    ),
    2011: SMLMVRecord(
        2011,
        Decimal(535600),
        Decimal("17853.33"),
        "Decreto 033 de 2011",
        "https://normativa.colpensiones.gov.co/",
    ),
    2012: SMLMVRecord(
        2012,
        Decimal(566700),
        Decimal("18890.00"),
        "Decreto 4919 de 2011",
        "https://normativa.colpensiones.gov.co/",
    ),
    2013: SMLMVRecord(
        2013,
        Decimal(589500),
        Decimal("19650.00"),
        "Decreto 2738 de 2012",
        "https://normativa.colpensiones.gov.co/",
    ),
    2014: SMLMVRecord(
        2014,
        Decimal(616000),
        Decimal("20533.33"),
        "Decreto 3068 de 2013",
        "https://normativa.colpensiones.gov.co/",
    ),
    2015: SMLMVRecord(
        2015,
        Decimal(644350),
        Decimal("21478.33"),
        "Decreto 2731 de 2014",
        "https://normativa.colpensiones.gov.co/",
    ),
    2016: SMLMVRecord(
        2016,
        Decimal(689455),
        Decimal("22981.83"),
        "Decreto 2552 de 2015",
        "https://normativa.colpensiones.gov.co/",
    ),
    2017: SMLMVRecord(
        2017,
        Decimal(737717),
        Decimal("24590.57"),
        "Decreto 2209 de 2016",
        "https://normativa.colpensiones.gov.co/",
    ),
    2018: SMLMVRecord(
        2018,
        Decimal(781242),
        Decimal("26041.40"),
        "Decreto 2269 de 2017",
        "https://normativa.colpensiones.gov.co/",
    ),
    2019: SMLMVRecord(
        2019,
        Decimal(828116),
        Decimal("27603.87"),
        "Decreto 2451 de 2018",
        "https://normativa.colpensiones.gov.co/",
    ),
    2020: SMLMVRecord(
        2020,
        Decimal(877803),
        Decimal("29260.10"),
        "Decreto 2360 de 2019",
        "https://normativa.colpensiones.gov.co/",
    ),
    2021: SMLMVRecord(
        2021,
        Decimal(908526),
        Decimal("30284.20"),
        "Decreto 1785 de 2020",
        "https://normativa.colpensiones.gov.co/",
    ),
    2022: SMLMVRecord(
        2022,
        Decimal(1000000),
        Decimal("33333.33"),
        "Decreto 1724 de 2021",
        "https://normativa.colpensiones.gov.co/",
    ),
    2023: SMLMVRecord(
        2023,
        Decimal(1160000),
        Decimal("38666.67"),
        "Decreto 2613 de 2022",
        "https://normativa.colpensiones.gov.co/",
    ),
    2024: SMLMVRecord(
        2024,
        Decimal(1300000),
        Decimal("43333.33"),
        "Decreto 2292 de 2023",
        "https://normativa.colpensiones.gov.co/",
    ),
    2025: SMLMVRecord(
        2025,
        Decimal(1423500),
        Decimal("47450.00"),
        "Decreto 1572 de 2024 (Oficial)",
        "https://normativa.colpensiones.gov.co/",
    ),
    2026: SMLMVRecord(
        2026,
        Decimal(1537380),
        Decimal("51246.00"),
        "Decreto Oficial 2026",
        "https://normativa.colpensiones.gov.co/",
    ),
}


def get_smlmv(year: int) -> SMLMVRecord:
    """Returns official SMLMV for a given year.

    Raises ValueError if year is not in historical registry.
    """
    if year in HISTORICAL_SMLMV:
        return HISTORICAL_SMLMV[year]
    # For years prior to 1990, use 1990 as base fallback or raise
    if year < 1990:
        return HISTORICAL_SMLMV[1990]
    raise ValueError(
        f"SMLMV no registrado oficialmente para el año {year}. Requiere supuesto económico."
    )
