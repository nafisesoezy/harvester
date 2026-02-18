from pystac_client import Client

def harvest_stac(url, max_records=20):
    client = Client.open(url)
    items = list(client.search().items())
    return [i.to_dict() for i in items[:max_records]]
