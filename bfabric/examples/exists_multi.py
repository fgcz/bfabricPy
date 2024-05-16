from bfabric import BfabricAPIEngineType, Bfabric
from bfabric.bfabric import get_system_auth
from bfabric.experimental.multi_query import MultiQuery


config, auth = get_system_auth(config_env="TEST")

b1 = MultiQuery(Bfabric(config, auth, engine=BfabricAPIEngineType.SUDS))
b2 = MultiQuery(Bfabric(config, auth, engine=BfabricAPIEngineType.ZEEP))


###################
# Testing IDs
###################

# target_user_ids = [1,2,3,4,5, 12345]
#
# response1 = b1.exists("user", 'id', target_user_ids)
# response2 = b2.exists("user", 'id', target_user_ids)
#
# print(response1)
# print(response2)

###################
# Testing Names
###################

target_workunit_names = ["tomcat", "tomcat2"]

response1 = b1.exists_multi("workunit", "name", target_workunit_names)
response2 = b2.exists_multi("workunit", "name", target_workunit_names)

print(response1)
print(response2)
