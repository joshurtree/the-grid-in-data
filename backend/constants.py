from datetime import timedelta
import os
from dataclasses import dataclass
from typing import Self
from dataclasses import field

@dataclass(frozen=True)
class GenerationType:
    code: str
    label: str
    sub_types: tuple[str, ...] = field(default_factory=tuple)
    legacy: bool = False

    def to_dict(self: Self) -> dict:
        return {
            'code': self.code,
            'label': self.label,
            'sub_types': self.sub_types or tuple(),
        }

    def use_alias(self: Self, alias: str):
        return GenerationType(code=alias, label=self.label, sub_types=self.sub_types)

def to_dict(generation_types: list[GenerationType], include_sub_types: bool = False) -> dict:
    generation_types_dict = {gt.code: gt.label for gt in generation_types} 
    
    if include_sub_types:
        for gt in generation_types:
            for sub_type in gt.sub_types:
                generation_types_dict[sub_type] = gt.label

    return generation_types_dict

interconnectors = ('INT', 'INTELE', 'INTELEC', 'INTEW', 'INTFR', 'INTGRNL', 'INTIFA2', 'INTIRL', 'INTNED', 'INTNEM', 'INTNSL', 'INTVKL')
COAL = GenerationType(code='COAL', label='Coal', legacy=True)
OIL = GenerationType(code='OIL', label='Oil', legacy=True)
NUCLEAR = GenerationType(code='NUCLEAR', label='Nuclear')
WIND = GenerationType(code='WIND', label='Wind')
IMPORTS = GenerationType(code='IMPORTS', label='Imports', sub_types=interconnectors)
BIOMASS = GenerationType(code='BIOMASS', label='Biomass')
GAS = GenerationType(code='GAS', label='Gas', sub_types=('CCGT', 'OCGT', 'RGAS'))
WIND_EMB = GenerationType(code='WIND_EMB', label='Embedded Wind')
STORAGE = GenerationType(code='STORAGE', label='Storage', sub_types=('PS', 'BESS'))
PS = GenerationType(code='PS', label='Pumped Storage')
CCGT = GenerationType(code='CCGT', label='Combined Cycle Gas Turbine')
OCGT = GenerationType(code='OCGT', label='Open Cycle Gas Turbine')
RGAS = GenerationType(code='RGAS', label='Reciprocating Gas Engine')
HYDRO = GenerationType(code='HYDRO', label='Hydro')
BESS = GenerationType(code='BESS', label='Battery Energy Storage System')
LOW_CARBON = GenerationType(code='LOW_CARBON', label='Low Carbon', sub_types=('NUCLEAR', 'WIND', 'WIND_EMB', 'HYDRO', 'SOLAR'))
RENEWABLE = GenerationType(code='RENEWABLE', label='Renewable', sub_types=('WIND', 'WIND_EMB', 'HYDRO', 'SOLAR'))
SOLAR = GenerationType(code='SOLAR', label='Solar')
FOSSIL = GenerationType(code='FOSSIL', label='Fossil', sub_types=('GAS', 'CCGT', 'OCGT', 'COAL', 'RGAS', 'OIL'))


NESO_GENERATION_TYPES = to_dict([COAL, NUCLEAR, WIND, WIND_EMB, GAS, IMPORTS, BIOMASS, STORAGE, HYDRO, LOW_CARBON, RENEWABLE, FOSSIL, SOLAR])
ELEXON_GENERATION_TYPES = to_dict([COAL, NUCLEAR, WIND, IMPORTS, BIOMASS, PS, CCGT, OCGT, HYDRO.use_alias('HNPSHYD')], include_sub_types=True)
ALL_GENERATION_TYPES = to_dict([COAL, NUCLEAR, WIND, WIND_EMB, GAS, IMPORTS, BIOMASS, STORAGE, PS, CCGT, OCGT, RGAS, HYDRO, LOW_CARBON, RENEWABLE, FOSSIL, SOLAR])

GENERATION_TYPE_GROUPS = [
    {
        'types': [GAS, CCGT, OCGT],
        'label': 'Gas',
        'colour': '#FF1F0F'
    },
    {
        'types': [COAL],
        'label': 'Coal',
        'colour': '#000000'
    },
    {
        'types': [WIND],
        'label': 'Wind',
        'colour': '#1718FF'
    },
    {
        'types': [HYDRO],
        'label': 'Hydro',
        'colour': '#9467BD'
    },
    {
        'types': [NUCLEAR],
        'label': 'Nuclear',
        'colour': '#10FF80'
    },
    {
        'types': [SOLAR],
        'label': 'Solar',       
        'colour': '#BCBD22'
    },  
    {
        'types': [PS, BESS],
        'label': 'Storage',
        'colour': '#17BECF'
    },
    {
        'types': [IMPORTS],
        'label': 'Imports',
        'colour': '#10564B'
    },
    {
        'types': [BIOMASS],
        'label': 'Biomass',
        'colour': '#808080'
    }
]

GENERATION_SUPER_GROUPS = {
    'Fossil Fuels': [GAS, CCGT, OCGT, COAL],
    'Low Carbon': [WIND, HYDRO, NUCLEAR, SOLAR],
    'Other': [PS, BESS, IMPORTS, BIOMASS],
}

GENERATION_COLOURS = {fuel_type: group['colour'] for group in GENERATION_TYPE_GROUPS for fuel_type in group['types']}

PERIOD_GROUPS = {
    'Hour': timedelta(hours=1),
    'Day': timedelta(days=1),
    'Week': timedelta(weeks=1),
    'Month': timedelta(days=30),
    'Quarter': timedelta(days=90),
    'Year': timedelta(days=365),
}

RAW_DATA_PATH = os.path.join('data', 'raw')
PROCESSED_DATA_PATH = os.path.join('data', 'processed')
MANUAL_DATA_PATH = os.path.join('data', 'manual')
METRIC_PATH = os.path.join('data', 'metrics')

INFLATORS = {
    2012: 1.0,
    2013: 1.026,
    2014: 1.041,
    2015: 1.041,
    2016: 1.048,
    2017: 1.076,
    2018: 1.103,
    2019: 1.122,
    2020: 1.132,
    2021: 1.161,    
    2022: 1.261,
    2023: 1.376,
    2024: 1.396,
    2025: 1.441,
    2026: 1.482,
    2027: 1.51, # Estimated based on previous years' trends
    2028: 1.53,
    2029: 1.55,
    2030: 1.58,
    2031: 1.61,
    2032: 1.64
}


if __name__ == "__main__":
    print("ELEXON_GENERATION_TYPES:", ELEXON_GENERATION_TYPES)
    print("NESO_GENERATION_TYPES:", NESO_GENERATION_TYPES)

DATE_FIELD = "Date"
DATETIME_FIELD = "Date and Time"
