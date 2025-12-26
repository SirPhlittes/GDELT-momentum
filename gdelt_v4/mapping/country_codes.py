"""
GDELT v4.3.1 Country Code Mapping
==================================
Centralized FIPS to ISO-3 country code conversion.

v4.3.1 "Broken Circuit" Fix:
- Added country centroid coordinates for fallback when lat/lon is missing
- get_country_centroid() function for Gaia globe visualization

GDELT uses FIPS 10-4 codes (2-letter), but Plotly choropleth maps
require ISO-3 codes (3-letter). This module provides the mapping.

Author: Philip Hendrik Littau
Version: 4.3.1
"""

from __future__ import annotations

from typing import Dict, Optional, List

import pandas as pd


# FIPS 10-4 to ISO-3 country code mapping
FIPS_TO_ISO3: Dict[str, str] = {
    # A
    "AF": "AFG",  # Afghanistan
    "AL": "ALB",  # Albania
    "AG": "DZA",  # Algeria
    "AQ": "ASM",  # American Samoa
    "AN": "AND",  # Andorra
    "AO": "AGO",  # Angola
    "AV": "AIA",  # Anguilla
    "AY": "ATA",  # Antarctica
    "AC": "ATG",  # Antigua and Barbuda
    "AR": "ARG",  # Argentina
    "AM": "ARM",  # Armenia
    "AA": "ABW",  # Aruba
    "AS": "AUS",  # Australia
    "AU": "AUT",  # Austria
    "AJ": "AZE",  # Azerbaijan
    
    # B
    "BF": "BHS",  # Bahamas
    "BA": "BHR",  # Bahrain
    "BG": "BGD",  # Bangladesh
    "BB": "BRB",  # Barbados
    "BO": "BLR",  # Belarus
    "BE": "BEL",  # Belgium
    "BH": "BLZ",  # Belize
    "BN": "BEN",  # Benin
    "BD": "BMU",  # Bermuda
    "BT": "BTN",  # Bhutan
    "BL": "BOL",  # Bolivia
    "BK": "BIH",  # Bosnia and Herzegovina
    "BC": "BWA",  # Botswana
    "BR": "BRA",  # Brazil
    "BX": "BRN",  # Brunei
    "BU": "BGR",  # Bulgaria
    "UV": "BFA",  # Burkina Faso
    "BM": "MMR",  # Burma (Myanmar)
    "BY": "BDI",  # Burundi
    
    # C
    "CB": "KHM",  # Cambodia
    "CM": "CMR",  # Cameroon
    "CA": "CAN",  # Canada
    "CV": "CPV",  # Cape Verde
    "CJ": "CYM",  # Cayman Islands
    "CT": "CAF",  # Central African Republic
    "CD": "TCD",  # Chad
    "CI": "CHL",  # Chile
    "CH": "CHN",  # China
    "CO": "COL",  # Colombia
    "CN": "COM",  # Comoros
    "CG": "COD",  # Congo (DRC)
    "CF": "COG",  # Congo (Republic)
    "CW": "COK",  # Cook Islands
    "CS": "CRI",  # Costa Rica
    "IV": "CIV",  # Cote d'Ivoire
    "HR": "HRV",  # Croatia
    "CU": "CUB",  # Cuba
    "CY": "CYP",  # Cyprus
    "EZ": "CZE",  # Czech Republic
    
    # D
    "DA": "DNK",  # Denmark
    "DJ": "DJI",  # Djibouti
    "DO": "DMA",  # Dominica
    "DR": "DOM",  # Dominican Republic
    
    # E
    "EC": "ECU",  # Ecuador
    "EG": "EGY",  # Egypt
    "ES": "SLV",  # El Salvador
    "EK": "GNQ",  # Equatorial Guinea
    "ER": "ERI",  # Eritrea
    "EN": "EST",  # Estonia
    "ET": "ETH",  # Ethiopia
    
    # F
    "FK": "FLK",  # Falkland Islands
    "FO": "FRO",  # Faroe Islands
    "FJ": "FJI",  # Fiji
    "FI": "FIN",  # Finland
    "FR": "FRA",  # France
    "FP": "PYF",  # French Polynesia
    
    # G
    "GB": "GAB",  # Gabon
    "GA": "GMB",  # Gambia
    "GG": "GEO",  # Georgia
    "GM": "DEU",  # Germany
    "GH": "GHA",  # Ghana
    "GI": "GIB",  # Gibraltar
    "GR": "GRC",  # Greece
    "GL": "GRL",  # Greenland
    "GJ": "GRD",  # Grenada
    "GQ": "GUM",  # Guam
    "GT": "GTM",  # Guatemala
    "GV": "GIN",  # Guinea
    "PU": "GNB",  # Guinea-Bissau
    "GY": "GUY",  # Guyana
    
    # H
    "HA": "HTI",  # Haiti
    "HO": "HND",  # Honduras
    "HK": "HKG",  # Hong Kong
    "HU": "HUN",  # Hungary
    
    # I
    "IC": "ISL",  # Iceland
    "IN": "IND",  # India
    "ID": "IDN",  # Indonesia
    "IR": "IRN",  # Iran
    "IZ": "IRQ",  # Iraq
    "EI": "IRL",  # Ireland
    "IS": "ISR",  # Israel
    "IT": "ITA",  # Italy
    
    # J
    "JM": "JAM",  # Jamaica
    "JA": "JPN",  # Japan
    "JO": "JOR",  # Jordan
    
    # K
    "KZ": "KAZ",  # Kazakhstan
    "KE": "KEN",  # Kenya
    "KR": "KIR",  # Kiribati
    "KN": "PRK",  # North Korea
    "KS": "KOR",  # South Korea
    "KU": "KWT",  # Kuwait
    "KG": "KGZ",  # Kyrgyzstan
    
    # L
    "LA": "LAO",  # Laos
    "LG": "LVA",  # Latvia
    "LE": "LBN",  # Lebanon
    "LT": "LSO",  # Lesotho
    "LI": "LBR",  # Liberia
    "LY": "LBY",  # Libya
    "LS": "LIE",  # Liechtenstein
    "LH": "LTU",  # Lithuania
    "LU": "LUX",  # Luxembourg
    
    # M
    "MC": "MAC",  # Macau
    "MK": "MKD",  # North Macedonia
    "MA": "MDG",  # Madagascar
    "MI": "MWI",  # Malawi
    "MY": "MYS",  # Malaysia
    "MV": "MDV",  # Maldives
    "ML": "MLI",  # Mali
    "MT": "MLT",  # Malta
    "RM": "MHL",  # Marshall Islands
    "MR": "MRT",  # Mauritania
    "MP": "MUS",  # Mauritius
    "MX": "MEX",  # Mexico
    "FM": "FSM",  # Micronesia
    "MD": "MDA",  # Moldova
    "MN": "MCO",  # Monaco
    "MG": "MNG",  # Mongolia
    "MJ": "MNE",  # Montenegro
    "MH": "MSR",  # Montserrat
    "MO": "MAR",  # Morocco
    "MZ": "MOZ",  # Mozambique
    
    # N
    "WA": "NAM",  # Namibia
    "NR": "NRU",  # Nauru
    "NP": "NPL",  # Nepal
    "NL": "NLD",  # Netherlands
    "NC": "NCL",  # New Caledonia
    "NZ": "NZL",  # New Zealand
    "NU": "NIC",  # Nicaragua
    "NG": "NER",  # Niger
    "NI": "NGA",  # Nigeria
    "NE": "NIU",  # Niue
    "NF": "NFK",  # Norfolk Island
    "CQ": "MNP",  # Northern Mariana Islands
    "NO": "NOR",  # Norway
    
    # O
    "MU": "OMN",  # Oman
    
    # P
    "PK": "PAK",  # Pakistan
    "PS": "PLW",  # Palau
    "PM": "PAN",  # Panama
    "PP": "PNG",  # Papua New Guinea
    "PA": "PRY",  # Paraguay
    "PE": "PER",  # Peru
    "RP": "PHL",  # Philippines
    "PC": "PCN",  # Pitcairn Islands
    "PL": "POL",  # Poland
    "PO": "PRT",  # Portugal
    "RQ": "PRI",  # Puerto Rico
    
    # Q
    "QA": "QAT",  # Qatar
    
    # R
    "RO": "ROU",  # Romania
    "RS": "RUS",  # Russia
    "RW": "RWA",  # Rwanda
    
    # S
    "SC": "KNA",  # Saint Kitts and Nevis
    "ST": "LCA",  # Saint Lucia
    "VC": "VCT",  # Saint Vincent
    "WS": "WSM",  # Samoa
    "SM": "SMR",  # San Marino
    "TP": "STP",  # Sao Tome and Principe
    "SA": "SAU",  # Saudi Arabia
    "SG": "SEN",  # Senegal
    "RI": "SRB",  # Serbia
    "SE": "SYC",  # Seychelles
    "SL": "SLE",  # Sierra Leone
    "SN": "SGP",  # Singapore
    "LO": "SVK",  # Slovakia
    "SI": "SVN",  # Slovenia
    "BP": "SLB",  # Solomon Islands
    "SO": "SOM",  # Somalia
    "SF": "ZAF",  # South Africa
    "OD": "SSD",  # South Sudan
    "SP": "ESP",  # Spain
    "CE": "LKA",  # Sri Lanka
    "SU": "SDN",  # Sudan
    "NS": "SUR",  # Suriname
    "WZ": "SWZ",  # Eswatini
    "SW": "SWE",  # Sweden
    "SZ": "CHE",  # Switzerland
    "SY": "SYR",  # Syria
    
    # T
    "TW": "TWN",  # Taiwan
    "TI": "TJK",  # Tajikistan
    "TZ": "TZA",  # Tanzania
    "TH": "THA",  # Thailand
    "TT": "TLS",  # Timor-Leste
    "TO": "TGO",  # Togo
    "TL": "TKL",  # Tokelau
    "TN": "TON",  # Tonga
    "TD": "TTO",  # Trinidad and Tobago
    "TS": "TUN",  # Tunisia
    "TU": "TUR",  # Turkey
    "TX": "TKM",  # Turkmenistan
    "TK": "TCA",  # Turks and Caicos
    "TV": "TUV",  # Tuvalu
    
    # U
    "UG": "UGA",  # Uganda
    "UP": "UKR",  # Ukraine
    "AE": "ARE",  # United Arab Emirates
    "UK": "GBR",  # United Kingdom
    "US": "USA",  # United States
    "UY": "URY",  # Uruguay
    "UZ": "UZB",  # Uzbekistan
    
    # V
    "NH": "VUT",  # Vanuatu
    "VT": "VAT",  # Vatican City
    "VE": "VEN",  # Venezuela
    "VM": "VNM",  # Vietnam
    "VI": "VGB",  # British Virgin Islands
    "VQ": "VIR",  # US Virgin Islands
    
    # W
    "WF": "WLF",  # Wallis and Futuna
    "WI": "ESH",  # Western Sahara
    
    # Y
    "YM": "YEM",  # Yemen
    
    # Z
    "ZA": "ZMB",  # Zambia
    "ZI": "ZWE",  # Zimbabwe
    
    # Special codes
    "XX": "XXX",  # Unknown
}

# ISO-3 to country name mapping
ISO3_TO_NAME: Dict[str, str] = {
    "AFG": "Afghanistan",
    "ALB": "Albania",
    "DZA": "Algeria",
    "AND": "Andorra",
    "AGO": "Angola",
    "ARG": "Argentina",
    "ARM": "Armenia",
    "AUS": "Australia",
    "AUT": "Austria",
    "AZE": "Azerbaijan",
    "BHS": "Bahamas",
    "BHR": "Bahrain",
    "BGD": "Bangladesh",
    "BRB": "Barbados",
    "BLR": "Belarus",
    "BEL": "Belgium",
    "BLZ": "Belize",
    "BEN": "Benin",
    "BTN": "Bhutan",
    "BOL": "Bolivia",
    "BIH": "Bosnia and Herzegovina",
    "BWA": "Botswana",
    "BRA": "Brazil",
    "BRN": "Brunei",
    "BGR": "Bulgaria",
    "BFA": "Burkina Faso",
    "MMR": "Myanmar",
    "BDI": "Burundi",
    "KHM": "Cambodia",
    "CMR": "Cameroon",
    "CAN": "Canada",
    "CPV": "Cape Verde",
    "CAF": "Central African Republic",
    "TCD": "Chad",
    "CHL": "Chile",
    "CHN": "China",
    "COL": "Colombia",
    "COM": "Comoros",
    "COD": "DR Congo",
    "COG": "Congo",
    "CRI": "Costa Rica",
    "CIV": "Ivory Coast",
    "HRV": "Croatia",
    "CUB": "Cuba",
    "CYP": "Cyprus",
    "CZE": "Czech Republic",
    "DNK": "Denmark",
    "DJI": "Djibouti",
    "DOM": "Dominican Republic",
    "ECU": "Ecuador",
    "EGY": "Egypt",
    "SLV": "El Salvador",
    "GNQ": "Equatorial Guinea",
    "ERI": "Eritrea",
    "EST": "Estonia",
    "ETH": "Ethiopia",
    "FJI": "Fiji",
    "FIN": "Finland",
    "FRA": "France",
    "GAB": "Gabon",
    "GMB": "Gambia",
    "GEO": "Georgia",
    "DEU": "Germany",
    "GHA": "Ghana",
    "GRC": "Greece",
    "GRL": "Greenland",
    "GTM": "Guatemala",
    "GIN": "Guinea",
    "GNB": "Guinea-Bissau",
    "GUY": "Guyana",
    "HTI": "Haiti",
    "HND": "Honduras",
    "HKG": "Hong Kong",
    "HUN": "Hungary",
    "ISL": "Iceland",
    "IND": "India",
    "IDN": "Indonesia",
    "IRN": "Iran",
    "IRQ": "Iraq",
    "IRL": "Ireland",
    "ISR": "Israel",
    "ITA": "Italy",
    "JAM": "Jamaica",
    "JPN": "Japan",
    "JOR": "Jordan",
    "KAZ": "Kazakhstan",
    "KEN": "Kenya",
    "PRK": "North Korea",
    "KOR": "South Korea",
    "KWT": "Kuwait",
    "KGZ": "Kyrgyzstan",
    "LAO": "Laos",
    "LVA": "Latvia",
    "LBN": "Lebanon",
    "LSO": "Lesotho",
    "LBR": "Liberia",
    "LBY": "Libya",
    "LIE": "Liechtenstein",
    "LTU": "Lithuania",
    "LUX": "Luxembourg",
    "MKD": "North Macedonia",
    "MDG": "Madagascar",
    "MWI": "Malawi",
    "MYS": "Malaysia",
    "MDV": "Maldives",
    "MLI": "Mali",
    "MLT": "Malta",
    "MRT": "Mauritania",
    "MUS": "Mauritius",
    "MEX": "Mexico",
    "MDA": "Moldova",
    "MCO": "Monaco",
    "MNG": "Mongolia",
    "MNE": "Montenegro",
    "MAR": "Morocco",
    "MOZ": "Mozambique",
    "NAM": "Namibia",
    "NPL": "Nepal",
    "NLD": "Netherlands",
    "NZL": "New Zealand",
    "NIC": "Nicaragua",
    "NER": "Niger",
    "NGA": "Nigeria",
    "NOR": "Norway",
    "OMN": "Oman",
    "PAK": "Pakistan",
    "PAN": "Panama",
    "PNG": "Papua New Guinea",
    "PRY": "Paraguay",
    "PER": "Peru",
    "PHL": "Philippines",
    "POL": "Poland",
    "PRT": "Portugal",
    "QAT": "Qatar",
    "ROU": "Romania",
    "RUS": "Russia",
    "RWA": "Rwanda",
    "SAU": "Saudi Arabia",
    "SEN": "Senegal",
    "SRB": "Serbia",
    "SYC": "Seychelles",
    "SLE": "Sierra Leone",
    "SGP": "Singapore",
    "SVK": "Slovakia",
    "SVN": "Slovenia",
    "SOM": "Somalia",
    "ZAF": "South Africa",
    "SSD": "South Sudan",
    "ESP": "Spain",
    "LKA": "Sri Lanka",
    "SDN": "Sudan",
    "SUR": "Suriname",
    "SWZ": "Eswatini",
    "SWE": "Sweden",
    "CHE": "Switzerland",
    "SYR": "Syria",
    "TWN": "Taiwan",
    "TJK": "Tajikistan",
    "TZA": "Tanzania",
    "THA": "Thailand",
    "TLS": "Timor-Leste",
    "TGO": "Togo",
    "TON": "Tonga",
    "TTO": "Trinidad and Tobago",
    "TUN": "Tunisia",
    "TUR": "Turkey",
    "TKM": "Turkmenistan",
    "UGA": "Uganda",
    "UKR": "Ukraine",
    "ARE": "UAE",
    "GBR": "United Kingdom",
    "USA": "United States",
    "URY": "Uruguay",
    "UZB": "Uzbekistan",
    "VEN": "Venezuela",
    "VNM": "Vietnam",
    "YEM": "Yemen",
    "ZMB": "Zambia",
    "ZWE": "Zimbabwe",
}

# v4.3.1: Country centroids (approximate lat, lon) for fallback visualization
# When GDELT doesn't provide precise coordinates, use country center
ISO3_TO_CENTROID: Dict[str, tuple] = {
    "AFG": (33.0, 65.0),
    "ALB": (41.0, 20.0),
    "DZA": (28.0, 3.0),
    "AGO": (-12.5, 18.5),
    "ARG": (-34.0, -64.0),
    "ARM": (40.0, 45.0),
    "AUS": (-25.0, 133.0),
    "AUT": (47.5, 13.5),
    "AZE": (40.5, 47.5),
    "BHS": (24.0, -76.0),
    "BHR": (26.0, 50.5),
    "BGD": (24.0, 90.0),
    "BLR": (53.0, 28.0),
    "BEL": (50.5, 4.5),
    "BEN": (9.5, 2.2),
    "BOL": (-17.0, -65.0),
    "BIH": (44.0, 18.0),
    "BWA": (-22.0, 24.0),
    "BRA": (-10.0, -55.0),
    "BGR": (42.5, 25.5),
    "BFA": (12.5, -1.5),
    "MMR": (21.0, 96.0),
    "BDI": (-3.5, 30.0),
    "KHM": (12.5, 105.0),
    "CMR": (6.0, 12.5),
    "CAN": (56.0, -106.0),
    "CAF": (7.0, 21.0),
    "TCD": (15.0, 19.0),
    "CHL": (-30.0, -71.0),
    "CHN": (35.0, 105.0),
    "COL": (4.0, -72.0),
    "COD": (-4.0, 22.0),
    "COG": (-1.0, 15.0),
    "CRI": (10.0, -84.0),
    "CIV": (7.5, -5.5),
    "HRV": (45.0, 15.5),
    "CUB": (22.0, -80.0),
    "CYP": (35.0, 33.0),
    "CZE": (49.5, 15.5),
    "DNK": (56.0, 10.0),
    "DOM": (19.0, -70.5),
    "ECU": (-2.0, -77.5),
    "EGY": (27.0, 30.0),
    "SLV": (13.8, -88.9),
    "ERI": (15.0, 39.0),
    "EST": (59.0, 26.0),
    "ETH": (8.0, 38.0),
    "FIN": (64.0, 26.0),
    "FRA": (46.0, 2.0),
    "GAB": (-1.0, 11.5),
    "GMB": (13.5, -16.5),
    "GEO": (42.0, 43.5),
    "DEU": (51.0, 9.0),
    "GHA": (8.0, -2.0),
    "GRC": (39.0, 22.0),
    "GTM": (15.5, -90.2),
    "GIN": (11.0, -10.0),
    "HTI": (19.0, -72.4),
    "HND": (14.5, -86.2),
    "HKG": (22.3, 114.2),
    "HUN": (47.0, 20.0),
    "ISL": (65.0, -18.0),
    "IND": (20.0, 77.0),
    "IDN": (-5.0, 120.0),
    "IRN": (32.0, 53.0),
    "IRQ": (33.0, 44.0),
    "IRL": (53.0, -8.0),
    "ISR": (31.5, 35.0),
    "ITA": (42.5, 12.5),
    "JPN": (36.0, 138.0),
    "JOR": (31.0, 36.0),
    "KAZ": (48.0, 68.0),
    "KEN": (1.0, 38.0),
    "PRK": (40.0, 127.0),
    "KOR": (36.5, 128.0),
    "KWT": (29.5, 47.8),
    "KGZ": (41.0, 75.0),
    "LAO": (18.0, 105.0),
    "LVA": (57.0, 25.0),
    "LBN": (33.9, 35.8),
    "LBR": (6.5, -9.5),
    "LBY": (27.0, 17.0),
    "LTU": (55.0, 24.0),
    "LUX": (49.8, 6.2),
    "MKD": (41.5, 22.0),
    "MDG": (-20.0, 47.0),
    "MWI": (-13.5, 34.0),
    "MYS": (4.0, 109.5),
    "MLI": (17.0, -4.0),
    "MLT": (35.9, 14.4),
    "MRT": (20.0, -12.0),
    "MEX": (23.0, -102.0),
    "MDA": (47.0, 29.0),
    "MNG": (46.0, 105.0),
    "MNE": (42.5, 19.3),
    "MAR": (32.0, -5.0),
    "MOZ": (-18.0, 35.0),
    "NAM": (-22.0, 17.0),
    "NPL": (28.0, 84.0),
    "NLD": (52.5, 5.8),
    "NZL": (-41.0, 174.0),
    "NIC": (12.8, -85.0),
    "NER": (16.0, 8.0),
    "NGA": (10.0, 8.0),
    "NOR": (62.0, 10.0),
    "OMN": (21.0, 57.0),
    "PAK": (30.0, 70.0),
    "PAN": (9.0, -80.0),
    "PNG": (-6.0, 147.0),
    "PRY": (-23.0, -58.0),
    "PER": (-10.0, -76.0),
    "PHL": (12.0, 122.0),
    "POL": (52.0, 20.0),
    "PRT": (39.5, -8.0),
    "QAT": (25.5, 51.2),
    "ROU": (46.0, 25.0),
    "RUS": (60.0, 100.0),
    "RWA": (-2.0, 30.0),
    "SAU": (24.0, 45.0),
    "SEN": (14.5, -14.5),
    "SRB": (44.0, 21.0),
    "SLE": (8.5, -12.0),
    "SGP": (1.4, 103.8),
    "SVK": (48.7, 19.5),
    "SVN": (46.0, 15.0),
    "SOM": (5.0, 46.0),
    "ZAF": (-29.0, 24.0),
    "SSD": (8.0, 30.0),
    "ESP": (40.0, -4.0),
    "LKA": (7.0, 81.0),
    "SDN": (15.0, 30.0),
    "SUR": (4.0, -56.0),
    "SWE": (62.0, 15.0),
    "CHE": (47.0, 8.2),
    "SYR": (35.0, 38.0),
    "TWN": (23.5, 121.0),
    "TJK": (39.0, 71.0),
    "TZA": (-6.0, 35.0),
    "THA": (15.0, 100.0),
    "TLS": (-8.5, 126.0),
    "TGO": (8.0, 1.2),
    "TUN": (34.0, 9.0),
    "TUR": (39.0, 35.0),
    "TKM": (40.0, 60.0),
    "UGA": (1.5, 32.5),
    "UKR": (49.0, 32.0),
    "ARE": (24.0, 54.0),
    "GBR": (54.0, -2.0),
    "USA": (38.0, -97.0),
    "URY": (-33.0, -56.0),
    "UZB": (41.5, 64.5),
    "VEN": (8.0, -66.0),
    "VNM": (16.0, 108.0),
    "YEM": (15.5, 48.0),
    "ZMB": (-15.0, 28.0),
    "ZWE": (-19.0, 29.5),
}


def get_country_centroid(iso3_code: str) -> tuple:
    """
    Get approximate centroid coordinates for a country.
    
    v4.3.1: Used as fallback when GDELT doesn't provide precise lat/lon.
    
    Args:
        iso3_code: 3-letter ISO-3 country code.
        
    Returns:
        Tuple of (latitude, longitude). Returns (0.0, 0.0) if not found.
    """
    if not iso3_code:
        return (0.0, 0.0)
    
    return ISO3_TO_CENTROID.get(iso3_code.upper(), (0.0, 0.0))


class CountryCodeMapper:
    """
    Utility class for country code conversions.
    
    Handles:
    - FIPS 10-4 to ISO-3 conversion
    - ISO-3 to country name lookup
    - DataFrame column conversion
    
    Example:
        >>> mapper = CountryCodeMapper()
        >>> mapper.fips_to_iso3("US")
        'USA'
        >>> mapper.get_country_name("USA")
        'United States'
        >>> df = mapper.convert_dataframe(df, 'country_code')
    """
    
    def __init__(self):
        """Initialize the mapper with default mappings."""
        self.fips_map = FIPS_TO_ISO3.copy()
        self.name_map = ISO3_TO_NAME.copy()
    
    def fips_to_iso3(self, fips_code: str) -> Optional[str]:
        """
        Convert a FIPS 10-4 code to ISO-3.
        
        Args:
            fips_code: 2-letter FIPS code.
            
        Returns:
            3-letter ISO-3 code or None if not found.
        """
        if not fips_code:
            return None
        
        fips_code = fips_code.strip().upper()
        
        # Already ISO-3?
        if len(fips_code) == 3:
            return fips_code
        
        return self.fips_map.get(fips_code)
    
    def get_country_name(self, iso3_code: str) -> Optional[str]:
        """
        Get country name from ISO-3 code.
        
        Args:
            iso3_code: 3-letter ISO-3 code.
            
        Returns:
            Country name or None if not found.
        """
        if not iso3_code:
            return None
        
        return self.name_map.get(iso3_code.upper())
    
    def convert_dataframe(
        self,
        df: pd.DataFrame,
        column: str,
        new_column: str = "iso3",
        add_name: bool = False,
    ) -> pd.DataFrame:
        """
        Convert country codes in a DataFrame column.
        
        Args:
            df: Input DataFrame.
            column: Column containing FIPS codes.
            new_column: Name for the new ISO-3 column.
            add_name: Whether to add a country name column.
            
        Returns:
            DataFrame with converted codes.
        """
        if column not in df.columns:
            return df
        
        df = df.copy()
        df[new_column] = df[column].apply(self.fips_to_iso3)
        
        # Fill NA with original value (might already be ISO-3)
        df[new_column] = df[new_column].fillna(df[column])
        
        if add_name:
            df["country_name"] = df[new_column].apply(self.get_country_name)
        
        return df
    
    def batch_convert(self, codes: List[str]) -> List[Optional[str]]:
        """
        Convert a list of FIPS codes to ISO-3.
        
        Args:
            codes: List of FIPS codes.
            
        Returns:
            List of ISO-3 codes.
        """
        return [self.fips_to_iso3(code) for code in codes]
    
    def get_centroid(self, iso3_code: str) -> tuple:
        """
        Get approximate centroid coordinates for a country.
        
        v4.3.1: Fallback when precise coordinates are not available.
        
        Args:
            iso3_code: 3-letter ISO-3 country code.
            
        Returns:
            Tuple of (latitude, longitude).
        """
        return get_country_centroid(iso3_code)
    
    def add_centroids_to_dataframe(
        self,
        df: pd.DataFrame,
        iso3_column: str = "iso3",
        lat_column: str = "latitude",
        lon_column: str = "longitude",
        overwrite_zeros: bool = True,
    ) -> pd.DataFrame:
        """
        Add centroid coordinates to a DataFrame.
        
        v4.3.1: Provides fallback coordinates when GDELT doesn't have precise lat/lon.
        
        Args:
            df: Input DataFrame with ISO-3 codes.
            iso3_column: Name of the column containing ISO-3 codes.
            lat_column: Name for latitude column.
            lon_column: Name for longitude column.
            overwrite_zeros: If True, replace 0/null values with centroids.
            
        Returns:
            DataFrame with latitude/longitude columns.
        """
        if df.empty or iso3_column not in df.columns:
            return df
        
        df = df.copy()
        
        # Get centroids for each row
        centroids = df[iso3_column].apply(
            lambda x: get_country_centroid(x) if x else (0.0, 0.0)
        )
        
        if lat_column not in df.columns:
            df[lat_column] = centroids.apply(lambda x: x[0])
            df[lon_column] = centroids.apply(lambda x: x[1])
        elif overwrite_zeros:
            # Fill in missing or zero coordinates
            centroid_lats = centroids.apply(lambda x: x[0])
            centroid_lons = centroids.apply(lambda x: x[1])
            
            # Replace zeros and nulls
            lat_mask = df[lat_column].isna() | (df[lat_column].abs() < 0.01)
            lon_mask = df[lon_column].isna() | (df[lon_column].abs() < 0.01)
            
            df.loc[lat_mask, lat_column] = centroid_lats[lat_mask]
            df.loc[lon_mask, lon_column] = centroid_lons[lon_mask]
        
        return df


# Singleton instance
_mapper_instance: Optional[CountryCodeMapper] = None


def get_mapper() -> CountryCodeMapper:
    """Get the global CountryCodeMapper instance."""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = CountryCodeMapper()
    return _mapper_instance

