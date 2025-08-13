import os, json, math
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def load_translations(path: str | None = None) -> pd.DataFrame:
    path = path or os.path.join(DATA_DIR, "translations.csv")
    return pd.read_csv(path)

def load_price_table(path: str | None = None) -> pd.DataFrame:
    path = path or os.path.join(DATA_DIR, "price_table.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    # Fallback simple table
    return pd.DataFrame({"PLN":[0,10,20,30], "EUR":[0,3,5,7], "BGN":[0,6,11,17],
                         "BAM":[0,6,11,17], "RON":[0,15,30,45], "CZK":[0,70,140,210],
                         "RSD":[0,350,700,1050], "HUF":[0,1200,2400,3600]})

def nearest_price(pln: float, table: pd.DataFrame) -> dict:
    # Pick nearest PLN row
    idx = (table["PLN"] - pln).abs().idxmin()
    row = table.loc[idx].to_dict()
    return {k: (int(v) if isinstance(v,(int,float)) and not math.isnan(v) else v) for k,v in row.items()}

def fmt_prices_from_pln(pln: float) -> dict:
    tbl = load_price_table()
    row = nearest_price(pln, tbl)
    if "PLN" not in row: row["PLN"] = pln
    # Ensure integer-like formatting (no decimals)
    for k in list(row.keys()):
        try:
            row[k] = int(float(row[k]))
        except Exception:
            pass
    return {
        "EUR": row.get("EUR", 0), "BGN": row.get("BGN", 0), "BAM": row.get("BAM", 0),
        "PLN": row.get("PLN", 0), "RON": row.get("RON", 0), "CZK": row.get("CZK", 0),
        "RSD": row.get("RSD", 0), "HUF": row.get("HUF", 0),
    }

def ean13_ok(code: str | None) -> bool:
    if not code or len(code)!=13 or not code.isdigit(): return False
    digits = [int(c) for c in code]
    s = sum((3 if (i%2) else 1) * d for i,d in enumerate(digits[:12]))
    check = (10 - (s % 10)) % 10
    return check == digits[12]

def ensure_semicolon_csv(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, sep=";")

