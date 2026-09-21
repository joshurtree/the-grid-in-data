from pprint import pprint
from ckanapi import RemoteCKAN

rc = RemoteCKAN('https://dp.lowcarboncontracts.uk/')
result = rc.action.datastore_search(
    resource_id="3f31f008-0b51-4b5b-9679-4be416509a75",
    limit=5,
)
pprint(result)