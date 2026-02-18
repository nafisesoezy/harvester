from sickle import Sickle
from datetime import datetime


def harvest_oai(url, max_records=20, start_date=None, end_date=None):
    print(f"📚 Harvesting OAI-PMH from {url}")
    print(f"⏱ From: {start_date} | Until: {end_date}")

    try:
        sickle = Sickle(url)

        # ✅ APPLY OAI DATE FILTERS AT PROTOCOL LEVEL
        params = {"metadataPrefix": "oai_dc"}

        if start_date:
            params["from"] = start_date   # MUST be YYYY-MM-DD

        if end_date:
            params["until"] = end_date   # MUST be YYYY-MM-DD

        records = sickle.ListRecords(**params)

        results = []
        for i, record in enumerate(records, start=1):
            if (max_records is not None) and (i > max_records):
                break
            results.append(record.raw)

        print(f"✅ Total OAI records harvested: {len(results)}")
        return results

    except Exception as e:
        print("⚠️ OAI-PMH harvest failed:", e)
        return []
