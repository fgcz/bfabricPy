import json
from zoneinfo import ZoneInfo
import datetime
import pandas as pd
from bfabric.bfabric2 import get_system_auth, Bfabric


def utc_to_server_time(utc_time: datetime.datetime, server_zone: ZoneInfo) -> str:
    server_time = utc_time.astimezone(server_zone)
    return server_time.strftime("%Y-%m-%dT%H:%M:%S.%f")


def main():
    config, auth = get_system_auth(config_env="TEST")
    client = Bfabric(config, auth)
    client.print_version_message()

    utc = datetime.datetime.utcnow()
    server_time = utc_to_server_time(utc, ZoneInfo("Europe/Zurich"))
    print(server_time)

    resp = client.read(endpoint="dataset", obj={"createdbefore": server_time}, max_results=10).to_list_dict(drop_empty=True)
    data = pd.DataFrame(resp)
    print(data)
    #print(json.dumps(resp, indent=2))


if __name__ == "__main__":
    main()