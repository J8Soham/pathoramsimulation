import csv
import os
from collections import Counter

CRIME_CSV = os.path.join(os.path.dirname(__file__), "datasets", "crime", "crimes.csv")
ORDERS_TBL = os.path.join(os.path.dirname(__file__), "datasets", "tpch", "tpch-dbgen", "orders.tbl")

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


def load_tpch_frequencies(max_rows=100000):
    freqs = Counter()
    with open(ORDERS_TBL, "r") as f:
        for i, line in enumerate(f):
            if i >= max_rows:
                break
            parts = line.strip().split("|")
            if len(parts) >= 6:
                order_priority = parts[5].strip()
                if order_priority:
                    freqs[order_priority] += 1
    return dict(freqs)


if __name__ == "__main__":
    crime = load_crime_frequencies()
    tpch = load_tpch_frequencies()
