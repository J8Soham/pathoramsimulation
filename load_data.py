import csv
import os
from collections import Counter

CRIME_CSV = os.path.join(os.path.dirname(__file__), "datasets", "crime", "crimes.csv")
ORDERS_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "orders.tbl")
LINEITEM_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "lineitem.tbl")
CUSTOMER_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "customer.tbl")
PART_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "part.tbl")
PARTSUP_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "partsupp.tbl")
SUPPLIER_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "supplier.tbl")
NATION_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "nation.tbl")
REGION_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "region.tbl")

def load_crime_frequencies(max_rows=100000):
    freqs = Counter()
    with open(CRIME_CSV, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            ptype = row.get("Primary Type", "").strip()
            if ptype:
                freqs[ptype] += 1
    return dict(freqs)

def get_tpch_source(table):
    if table == "orders":
        return ORDERS_TBL, 9
    elif table == "lineitem":
        return LINEITEM_TBL, 16
    elif table == "customer":
        return CUSTOMER_TBL, 8
    elif table == "part":
        return PART_TBL, 9
    elif table == "partsupp":
        return PARTSUP_TBL, 5
    elif table == "supplier":
        return SUPPLIER_TBL, 7
    elif table == "nation":
        return NATION_TBL, 4
    elif table == "region":
        return REGION_TBL, 3
    else:
        raise ValueError(f"Unknown table: {table}")


def load_tpch_frequencies(table, max_rows=100000):
    table_path, num_cols = get_tpch_source(table)
    freqs = {i: Counter() for i in range(num_cols)}
    
    with open(table_path, "r") as f:
        for row_idx, line in enumerate(f):
            if max_rows is not None and row_idx >= max_rows:
                break
            parts = line.rstrip("\n").split("|")
            for col_idx in range(min(num_cols, len(parts))):
                val = parts[col_idx].strip()
                if val:
                    freqs[col_idx][val] += 1
    return {i: dict(c) for i, c in freqs.items()}


if __name__ == "__main__":
    crime = load_crime_frequencies()
    tpch = load_tpch_frequencies("orders")
