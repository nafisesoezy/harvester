from owslib.csw import CatalogueServiceWeb

def harvest_csw(url, max_records=20):
    csw = CatalogueServiceWeb(url, timeout=30)
    csw.getrecords2(maxrecords=max_records)
    return [r.xml for r in csw.records.values()]
