"""Scan a customer's artifacts: list sheets, columns, row counts, head rows.

Usage: copy this file into the customer's assessment folder (or set CUSTOMER below)."""
from pathlib import Path
import pandas as pd
import openpyxl
import json
import sys

CUSTOMER = "<CUSTOMER>"  # e.g. "Contoso" — replace when copying into a customer engagement folder
CUST_DIR = Path(__file__).parent / "Customers" / CUSTOMER

def inspect_workbook(path: Path):
    print(f"\n{'='*80}\nFILE: {path.name}\n{'='*80}")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    print(f"Sheets ({len(wb.sheetnames)}): {wb.sheetnames}")
    for sn in wb.sheetnames:
        try:
            df = pd.read_excel(path, sheet_name=sn, engine="openpyxl")
        except Exception as e:
            print(f"\n--- Sheet: {sn!r} --- ERROR: {e}")
            continue
        print(f"\n--- Sheet: {sn!r}  rows={len(df)}  cols={len(df.columns)} ---")
        print("Columns:")
        for c in df.columns:
            print(f"  - {c!r}  (dtype={df[c].dtype}, non-null={df[c].notna().sum()})")
        if len(df) > 0:
            print("\nHead (first 5 rows):")
            with pd.option_context("display.max_columns", 50, "display.width", 200, "display.max_colwidth", 50):
                print(df.head(5).to_string())

for f in sorted(CUST_DIR.glob("*.xlsx")):
    inspect_workbook(f)
