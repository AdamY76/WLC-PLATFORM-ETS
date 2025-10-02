import pandas as pd
from sparql_client import insert_excel_cost

def import_uniformat_excel(path, phase="ConstructionCosts"):
    df = pd.read_excel(path)
    # Recherche des colonnes "GUID" et "COÛT" (ou "COUT" ou "COUTS" ou "COST")
    guid_col = None
    cost_col = None
    for col in df.columns:
        if "guid" in col.lower():
            guid_col = col
        if "cout" in col.lower() or "coût" in col.lower() or "cost" in col.lower():
            cost_col = col
    if guid_col is None or cost_col is None:
        raise Exception(f"Colonnes GUID ou COÛT non trouvées ({df.columns.tolist()})")
    inserted = []
    for idx, row in df.iterrows():
        guid = str(row[guid_col]).strip()
        try:
            cost = float(row[cost_col])
        except Exception:
            continue
        if guid and cost:
            insert_excel_cost(guid, cost)
            inserted.append((guid, cost))
    return {"inserted": inserted, "total": len(inserted)}
