"""
PDF → CSV extractor + Streamlit UI (MVP)
- Runs as a CLI: python backend/scripts/pep_data_app.py --in input.pdf --out out.csv
- Runs as a Streamlit app: streamlit run backend/scripts/pep_data_app.py
"""
from __future__ import annotations
import os, re, sys, io, argparse, datetime as dt
from typing import List, Dict, Any
import pandas as pd

# Optional deps for PDF; if missing, the CLI will explain
try:
    import pdfplumber
except Exception:
    pdfplumber = None

# Streamlit is optional; only used when launched via `streamlit run`
try:
    import streamlit as st
except Exception:
    st = None

# Local utils
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.append(SCRIPT_DIR)
from utils import (
    load_translations, load_price_table, ean13_ok, fmt_prices_from_pln,
    ensure_semicolon_csv
)

# ----- Config (adjust as you like) -----
CSV_COLUMNS = [
    "Order_ID","STYLE_CODE","COLOUR","Supplier_product_code","Item_classification",
    "Supplier_name","today_date","COLLECTION","COLOUR_SKU","STYLE","Batch","barcode",
    "EUR","BGN","BAM","PLN","RON","CZK","RSD","HUF","product_name"
]

# ----- Core Extraction -----
def extract_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Very lightweight example extractor.
    Replace/expand the regex rules to match your real PDFs.
    """
    if not pdfplumber:
        raise RuntimeError("pdfplumber not installed. Add it to requirements and reinstall.")

    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            try:
                text.append(page.extract_text() or "")
            except Exception:
                text.append("")
    blob = "\n".join(text)

    # Examples (adapt the patterns to your actual layout)
    def rx(pat, default=""):
        m = re.search(pat, blob, flags=re.I)
        return m.group(1).strip() if m else default

    order_id   = rx(r"ORDER[\s\-:]*ID\s*[:\-]\s*([A-Z0-9_\/\-]+)")
    style_code = rx(r"STYLE(?:\s*CODE)?\s*[:\-]\s*([A-Z0-9\-]+)")
    colour     = rx(r"COLOU?R\s*[:\-]\s*([A-Z0-9 \/\-]+)")
    supplier   = rx(r"Supplier(?:\s*name)?\s*[:\-]\s*([A-Z0-9 \-]+)")
    collection = rx(r"COLLECTION\s*[:\-]\s*([A-Z0-9 \-]+)")
    sku        = rx(r"(?:SKU|COLOUR\s*SKU)\s*[:\-]\s*([A-Z0-9 \-]+)")
    barcode    = rx(r"\b(\d{13})\b")
    item_cls   = rx(r"ITEM(?:\s*CLASSIFICATION)?\s*[:\-]\s*([A-Z0-9 \-]+)")
    style_name = rx(r"STYLE\s*[:\-]\s*([A-Z0-9 \-]+)")
    supplier_code = rx(r"Supplier[_\s\-]?product[_\s\-]?code\s*[:\-]\s*([A-Z0-9 \-]+)")
    handover_date = rx(r"(?:Handover|Tech Pack|Last Revision)\s*(?:Date)?\s*[:\-]\s*([0-9\/\-.]+)")

    # Batch – simple rule example (year+week); replace with your real rule
    today = dt.date.today()
    batch = f"{today.strftime('%y')}{today.strftime('%W')}"  # e.g., 2511

    # Default PLN (base) → convert to others
    base_pln = 0
    try:
        base_pln = float(rx(r"PLN\s*[:\-]?\s*([\d\.,]+)").replace(",", "."))
    except Exception:
        base_pln = 0

    prices = fmt_prices_from_pln(base_pln)

    # Product name — build from translations if available later
    product_name = ""

    row = {
        "Order_ID": order_id or "",
        "STYLE_CODE": style_code or "",
        "COLOUR": colour or "",
        "Supplier_product_code": supplier_code or "",
        "Item_classification": item_cls or "",
        "Supplier_name": supplier or "",
        "today_date": today.strftime("%Y-%m-%d"),
        "COLLECTION": collection or "",
        "COLOUR_SKU": sku or "",
        "STYLE": style_name or "",
        "Batch": batch,
        "barcode": barcode if ean13_ok(barcode) else "",
        "EUR": prices["EUR"],
        "BGN": prices["BGN"],
        "BAM": prices["BAM"],
        "PLN": prices["PLN"],
        "RON": prices["RON"],
        "CZK": prices["CZK"],
        "RSD": prices["RSD"],
        "HUF": prices["HUF"],
        "product_name": product_name,
    }
    return {"rows": [row]}

def to_dataframe(payload: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(payload["rows"])
    # Ensure all columns exist and order is fixed
    for c in CSV_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[CSV_COLUMNS]

def save_csv(df: pd.DataFrame, path: str):
    ensure_semicolon_csv(df, path)

# ----- CLI -----
def main_cli():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_pdf", required=True, help="Input PDF path")
    p.add_argument("--out", dest="out_csv", required=True, help="Output CSV path")
    args = p.parse_args()

    payload = extract_from_pdf(args.in_pdf)
    df = to_dataframe(payload)
    save_csv(df, args.out_csv)
    print(f"Saved: {args.out_csv}")

# ----- Streamlit App -----
def main_streamlit():
    st.set_page_config(page_title="PEPCO – PDF → CSV", layout="wide")
    st.title("PEPCO – PDF → CSV (MVP)")
    st.caption("Upload a PDF, review/edit rows, then export ;–delimited CSV for Illustrator.")

    col_u, col_cfg = st.columns([3, 1])
    with col_u:
        up = st.file_uploader("Upload PDF", type=["pdf"])
        if up:
            # Save temp
            tmp_path = os.path.join(os.getcwd(), f"_tmp_{up.name}")
            with open(tmp_path, "wb") as f:
                f.write(up.read())
            try:
                payload = extract_from_pdf(tmp_path)
                df = to_dataframe(payload)
                st.success("Data extracted. Review below.")
            except Exception as e:
                st.error(f"Extraction error: {e}")
                return

            st.subheader("Preview / Edit")
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Download CSV (; delimited)"):
                    csv_buf = io.StringIO()
                    edited.to_csv(csv_buf, index=False, sep=";")
                    st.download_button("Save CSV", csv_buf.getvalue().encode("utf-8"), file_name="pepco_data.csv", mime="text/csv")
            with c2:
                st.info("Next: feed this CSV to Illustrator Worker → PEPCO.jsx to render final PDF.")
    with col_cfg:
        st.markdown("### Lookups")
        st.markdown("- Translations & Price table are loaded in backend (`backend/data/*`).")
        st.markdown("- Edit rules in `utils.py`.")

if __name__ == "__main__":
    if "streamlit" in sys.argv[0]:  # launched by streamlit
        if st is None:
            raise SystemExit("Install streamlit first.")
        main_streamlit()
    else:
        main_cli()

