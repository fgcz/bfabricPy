from bfabric.bfabric2 import Bfabric, BfabricAPIEngineType, get_system_auth


config, auth = get_system_auth()

b1 = Bfabric(config, auth, engine = BfabricAPIEngineType.SUDS)
# b2 = Bfabric(config, auth, engine = BfabricAPIEngineType.ZEEP)

workunit1 = {'name': 'tomcat', 'applicationid': 2, 'description': 'is warm and fluffy', 'containerid': 123}
response = b1.save('workunit', workunit1)

print(response.results[0])


# target_user_ids = [1,2,3,4,5, 12345]
#
# response1 = b1.exists("user", target_user_ids)
# response2 = b2.exists("user", target_user_ids)
#
# print(response1)
# print(response2)