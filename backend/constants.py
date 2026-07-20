from datetime import timedelta
import os

GENERATION_TYPES = {
    'COAL': 'Coal',
    'NUCLEAR': 'Nuclear',
    'WIND': 'Wind',
    'HYDRO': 'Hydro',
    'IMPORTS': 'Imports',
    'BIOMASS': 'Biomass',
    'OTHER': 'Other',
    'SOLAR': 'Solar',
}

NESO_GENERATION_TYPES = GENERATION_TYPES | {
    'GAS': 'Gas',
    'WIND_EMB': 'Wind (Embedded)',
    'STORAGE': 'Storage',
    'FOSSIL': 'Fossil',
    'LOW_CARBON': 'Low Carbon',
    'RENEWABLE': 'Renewable',
}

ELEXON_GENERATION_TYPES = GENERATION_TYPES | {
    'CCGT': 'Combined Cycle Gas Turbine',
    'OCGT': 'Open Cycle Gas Turbine',
    'GAS': 'Gas (Other)',
    'BESS': 'Battery Energy Storage System',
    'INT': 'Interconnectors',
    'PS': 'Pumped Storage',
}

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

# GENERATION_COLOURS = {
#     'GAS': '#FF1F0F',
#     'CCGT': '#FF1F0F',
#     'OCGT': '#FF1F0F',
#     'COAL': '#000000',
#     'NUCLEAR': '#10FF80',
#     'WIND': '#1718FF',
#     'WIND_EMB': '#1718FF',
#     'HYDRO': '#9467BD',
#     'IMPORTS': '#10564B',
#     'BIOMASS': '#808080',
#     'OTHER': '#FFFFFF',
#     'SOLAR': '#BCBD22',
#     'STORAGE': '#17BECF',
#     'FOSSIL': '#FF7F0E',
#     'LOW_CARBON': '#2CA02C',
#     'RENEWABLE': '#D62728',
#     'BESS': '#17BECF',
#     'PS': '#17BECF',
# }

PERIOD_GROUPS = {
    'Hour': timedelta(hours=1),
    'Day': timedelta(days=1),
    'Week': timedelta(weeks=1),
    'Month': timedelta(days=30),
}

RAW_DATA_DIR = os.path.join('data', 'raw')
TRANSFORMED_DATA_DIR = os.path.join('data', 'transformed')
MANUAL_DATA_DIR = os.path.join('data', 'manual')