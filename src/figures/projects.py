# List upcoming renewable energy projects in the UK, including solar, wind, and hydroelectric projects. Provide details such as location, capacity, expected completion date, and any notable features or technologies being used.

import pandas as pd
from  datasources.system import repd_projects_source

projects = repd_projects_source.load_data()