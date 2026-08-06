from datetime import timedelta
import os
from dataclasses import dataclass
from typing import Self
from dataclasses import field

@dataclass
class GenerationType:
    code: str
    label: str
    sub_types: list[str] = field(default_factory=list)
    legacy: bool = False

    def to_dict(self: Self) -> dict:
        return {
            'code': self.code,
            'label': self.label,
            'sub_types': self.sub_types or []
        }

    def use_alias(self: Self, alias: str) -> str:
        return GenerationType(code=alias, label=self.label, sub_types=self.sub_types)

def to_dict(generation_types: list[GenerationType], include_sub_types: bool = False) -> dict:
    generation_types_dict = {gt.code: gt.label for gt in generation_types} 
    
    if include_sub_types:
        for gt in generation_types:
            for sub_type in gt.sub_types:
                generation_types_dict[sub_type] = gt.label

    return generation_types_dict

interconnectors = ['INT', 'INTELE', 'INTELEC', 'INTEW', 'INTFR', 'INTGRNL', 'INTIFA2', 'INTIRL', 'INTNED', 'INTNEM', 'INTNSL', 'INTVKL']
COAL = GenerationType(code='COAL', label='Coal', legacy=True)
OIL = GenerationType(code='OIL', label='Oil', legacy=True)
NUCLEAR = GenerationType(code='NUCLEAR', label='Nuclear')
WIND = GenerationType(code='WIND', label='Wind')
IMPORTS = GenerationType(code='IMPORTS', label='Imports', sub_types=interconnectors)
BIOMASS = GenerationType(code='BIOMASS', label='Biomass')
GAS = GenerationType(code='GAS', label='Gas', sub_types=['CCGT', 'OCGT', 'RGAS'])
WIND_EMB = GenerationType(code='WIND_EMB', label='Wind (Embedded)')
STORAGE = GenerationType(code='STORAGE', label='Storage', sub_types=['PS', 'BESS'])
PS = GenerationType(code='PS', label='Pumped Storage')
CCGT = GenerationType(code='CCGT', label='Combined Cycle Gas Turbine')
OCGT = GenerationType(code='OCGT', label='Open Cycle Gas Turbine')
RGAS = GenerationType(code='RGAS', label='Reciprocating Gas Engine')
HYDRO = GenerationType(code='HYDRO', label='Hydro')
BESS = GenerationType(code='BESS', label='Battery Energy Storage System')
LOW_CARBON = GenerationType(code='LOW_CARBON', label='Low Carbon', sub_types=['NUCLEAR', 'WIND', 'WIND_EMB', 'HYDRO', 'SOLAR'])
RENEWABLE = GenerationType(code='RENEWABLE', label='Renewable', sub_types=['WIND', 'WIND_EMB', 'HYDRO', 'SOLAR'])
SOLAR = GenerationType(code='SOLAR', label='Solar')
FOSSIL = GenerationType(code='FOSSIL', label='Fossil', sub_types=['GAS', 'CCGT', 'OCGT', 'COAL', 'RGAS', 'OIL'])


NESO_GENERATION_TYPES = to_dict([COAL, NUCLEAR, WIND, WIND_EMB, GAS, IMPORTS, BIOMASS, STORAGE, HYDRO, LOW_CARBON, RENEWABLE, FOSSIL, SOLAR])
ELEXON_GENERATION_TYPES = to_dict([COAL, NUCLEAR, WIND, IMPORTS, BIOMASS, PS, CCGT, OCGT, HYDRO.use_alias('HNPSHYD')], include_sub_types=True)
ALL_GENERATION_TYPES = to_dict([COAL, NUCLEAR, WIND, WIND_EMB, GAS, IMPORTS, BIOMASS, STORAGE, PS, CCGT, OCGT, RGAS, HYDRO, LOW_CARBON, RENEWABLE, FOSSIL, SOLAR])

GENERATION_TYPE_GROUPS = [
    {
        'types': ['GAS', 'CCGT', 'OCGT'],
        'label': 'Gas',
        'colour': '#FF1F0F'
    },
    {
        'types': ['COAL'],
        'label': 'Coal',
        'colour': '#000000'
    },
    {
        'types': ['WIND'],
        'label': 'Wind',
        'colour': '#1718FF'
    },
    {
        'types': ['HYDRO'],
        'label': 'Hydro',
        'colour': '#9467BD'
    },
    {
        'types': ['NUCLEAR'],
        'label': 'Nuclear',
        'colour': '#10FF80'
    },
    {
        'types': ['SOLAR'],
        'label': 'Solar',       
        'colour': '#BCBD22'
    },  
    {
        'types': ['PS', 'BESS'],
        'label': 'Storage',
        'colour': '#17BECF'
    },
    {
        'types': ['IMPORTS'],
        'label': 'Imports',
        'colour': '#10564B'
    },
    {
        'types': ['BIOMASS'],
        'label': 'Biomass',
        'colour': '#808080'
    }
]

GENERATION_SUPER_GROUPS = {
    'Fossil Fuels': ['GAS', 'CCGT', 'OCGT', 'COAL'],
    'Low Carbon': ['WIND', 'HYDRO', 'NUCLEAR', 'SOLAR'],
    'Other': ['PS', 'BESS', 'IMPORTS', 'BIOMASS'],
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

RAW_DATA_DIR = os.path.join('data', 'raw')
TRANSFORMED_DATA_DIR = os.path.join('data', 'transformed')
MANUAL_DATA_DIR = os.path.join('data', 'manual')

if __name__ == "__main__":
    print("ELEXON_GENERATION_TYPES:", ELEXON_GENERATION_TYPES)
    print("NESO_GENERATION_TYPES:", NESO_GENERATION_TYPES)
    print("COMPLETE_GENERATION_TYPES:", COMPLETE_GENERATION_TYPES)