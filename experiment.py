import random
import math
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from utils import adj_padding_volumes, query_recovery_attack, database_recovery_attack
from load_data import load_crime_frequencies, load_tpch_frequencies

NUM_QUERIES = 100
ALPHA_VALUES = [0, 1, 2, 3, 4]
X_VALUES = [1, 2, 4]


def build_sorted_array(keyword_volumes):
    M = []
    for keyword in sorted(keyword_volumes.keys()):
        for j in range(keyword_volumes[keyword]):
            M.append((keyword, f"doc_{j}"))
    odict = {}
    current_kw = None
    start = 0
    for i, (kw, _) in enumerate(M):
        if kw != current_kw:
            if current_kw is not None:
                odict[current_kw] = (start, i - start)
            current_kw = kw
            start = i
    if current_kw is not None:
        odict[current_kw] = (start, len(M) - start)
    return M, odict


def simulate_seal_access(alpha, M, odict, query_sequence):
    prp_key = AESGCM.generate_key(bit_length=128)
    prp = AESGCM(prp_key)
    num_orams = 1 << alpha

    def prp_to_oram(index):
        padded = str(index).encode().ljust(16, b'\x00')[:16]
        nonce = b'\x00' * 12
        encrypted = prp.encrypt(nonce, padded, None)
        if alpha == 0:
            return 0
        return encrypted[0] % num_orams

    index_to_oram = {}
    for i in range(len(M)):
        index_to_oram[i] = prp_to_oram(i)

    query_results_volumes = []
    query_results_tuples = []
    for kw in query_sequence:
        if kw not in odict:
            continue
        i_w, cnt_w = odict[kw]
        tuples = []
        for i in range(i_w, i_w + cnt_w):
            tuples.append({"oram_id": index_to_oram[i], "index": i})
        query_results_volumes.append((kw, cnt_w))
        query_results_tuples.append((kw, tuples))

    return query_results_volumes, query_results_tuples


def run_for_dataset(name, keyword_volumes):
    keywords = [kw for kw in keyword_volumes.keys() if kw != "__dummy_kw__"]
    print(f"\n{'='*60}")
    print(f"Dataset: {name}")
    print(f"Keywords: {len(keywords)}, Total records: {sum(keyword_volumes.values())}")
    print(f"{'='*60}")

    query_sequence = random.choices(
        keywords,
        weights=[keyword_volumes[kw] for kw in keywords],
        k=NUM_QUERIES
    )

    results = {}
    for x in X_VALUES:
        padded_volumes = adj_padding_volumes(keyword_volumes, x)

        M, odict = build_sorted_array(padded_volumes)

        for alpha in ALPHA_VALUES:
            qr_volumes, qr_tuples = simulate_seal_access(
                alpha, M, odict, query_sequence
            )

            qr_success = query_recovery_attack(padded_volumes, qr_volumes)
            dr_success = database_recovery_attack(padded_volumes, qr_tuples, alpha)

            key = f"a{alpha}_x{x}"
            results[key] = {
                "alpha": alpha,
                "x": x,
                "query_recovery": qr_success,
                "database_recovery": dr_success
            }
            print(f"  alpha={alpha}, x={x}: QR={qr_success:.2%}, DR={dr_success:.2%}")

    return results


def run_experiment():
    print("Loading datasets...")

    crime_freqs = load_crime_frequencies(max_rows=10000)
    tpch_freqs = load_tpch_frequencies(max_rows=10000)

    crime_results = run_for_dataset("Chicago Crime (Primary Type)", crime_freqs)
    tpch_results = run_for_dataset("TPC-H Orders (Order Priority)", tpch_freqs)

    all_results = {
        "crime": crime_results,
        "tpch": tpch_results
    }

    with open("results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nResults saved to results.json")


if __name__ == "__main__":
    run_experiment()
