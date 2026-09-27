from .datasource import DataLicence, DataProvider

open_government_licence = DataLicence(name="Open Government Licence", url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/")

neso_provider = DataProvider(
    name="National Energy System Operator", 
    short_name="NESO", url="https://neso.energy/data-portal/", 
    licence=open_government_licence
)
elexon_provider = DataProvider(
    name="Elexon", 
    short_name="BRMS",
    url="https://brms.elexon.co.uk/", 
    licence=DataLicence(name="Elexon Licence", url="https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/"),
    attribution="Contains BMRS data © Elexon Limited copyright and database right 2026"
)
ofgem_provider = DataProvider(
    name="Ofgem", 
    url="https://www.ofgem.gov.uk/", 
    licence=open_government_licence)
dukes_provider = DataProvider(
    name="Digest of UK Energy Statistics", 
    short_name="DUKES", 
    url="https://www.gov.uk/government/collections/digest-of-uk-energy-statistics-dukes", 
    licence=open_government_licence)
ons_provider = DataProvider(
    name="Office for National Statistics", 
    short_name="ONS", 
    url="https://www.ons.gov.uk/", 
    licence=open_government_licence)
ngeso_provider = DataProvider(
    name="National Grid ESO", 
    short_name="NG ESO", 
    url="https://www.nationalgrideso.com/"
)
poundf_provider = DataProvider(name="Poundf", url="https://www.poundf.co.uk/")
lccc_provider = DataProvider(
    name="Low Carbon Contracts Company", 
    short_name="LCCC", 
    url="https://www.lowcarboncontracts.uk/", 
    licence=open_government_licence
)
repd_provider = DataProvider(
    name="Renewable Energy Planning Database", 
    short_name="REPD", 
    url="https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract",
    licence=open_government_licence
)

nationalgas_provider = DataProvider(
    name="National Gas", 
    short_name="NGAS", 
    url="https://data.nationalgas.com/"
)
energy_trends_provider = DataProvider(
    name="Energy Trends", 
    short_name="Energy Trends", 
    url="https://www.gov.uk/government/statistics/energy-trends-section-6-renewables",
    licence=open_government_licence
)