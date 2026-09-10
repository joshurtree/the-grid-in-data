from datasources.datasource import DataProvider

neso_provider = DataProvider(name="National Energy System Operator", short_name="NESO", url="https://neso.energy/data-portal/")
elexon_provider = DataProvider(name="Elexon", url="https://brms.elexon.co.uk/")
ofgem_provider = DataProvider(name="Ofgem", url="https://www.ofgem.gov.uk/")
dukes_provider = DataProvider(name="Digest of UK Energy Statistics", short_name="DUKES", url="https://www.gov.uk/government/collections/digest-of-uk-energy-statistics-dukes")
ons_provider = DataProvider(name="Office for National Statistics", short_name="ONS", url="https://www.ons.gov.uk/")
ngeso_provider = DataProvider(name="National Grid ESO", short_name="NG ESO", url="https://www.nationalgrideso.com/")
poundf_provider = DataProvider(name="Poundf", url="https://www.poundf.com/")
lccc_provider = DataProvider(name="Low Carbon Contracts Company", short_name="LCCC", url="https://www.lowcarboncontracts.uk/")
repd_provider = DataProvider(name="Renewable Energy Planning Database", short_name="REPD", url="https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract")
nationalgas_provider = DataProvider(name="National Gas", short_name="NGAS", url="https://data.nationalgas.com/")