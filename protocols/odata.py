import requests

def harvest_odata(url, max_records=20):
    r = requests.get(url, timeout=10)
    data = r.json()
    return list(data.values())[:max_records]
