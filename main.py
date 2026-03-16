import random
import json
from client import Client
from client_seal import SealClient
from load_data import load_crime_frequencies, load_tpch_frequencies
from client_simulation import adj_padding_volumes, build_sorted_array, simulate_seal_access

def query_recovery_attack(padded_volumes, queries_with_volumes):
    T = dict(padded_volumes)
    correct = 0
    total = len(queries_with_volumes)
    for t_q, vol_q in queries_with_volumes:
        candidates = [kw for kw, v in T.items() if v == vol_q]
        if not candidates:
            continue
        q_prime = random.choice(candidates)
        T.pop(q_prime)
        if q_prime == t_q:
            correct += 1
    return correct / total if total > 0 else 0.0

def database_recovery_attack(padded_volumes, queries_with_tuples, alpha, index_to_oram):
    num_orams = 1 << alpha
    oram_groups = {}
    idx = 0
    for kw in sorted(padded_volumes.keys()):
        vol = padded_volumes[kw]
        for _ in range(vol):
            oram_id = index_to_oram[idx] # realized that we need to have 
            oram_groups.setdefault(oram_id, []).append({"idx": idx, "keyword": kw})
            idx += 1
    T = dict(padded_volumes)
    correct = 0
    total_tuples = 0
    for t_q, S_q in queries_with_tuples:
        vol_q = len(S_q)
        candidates = [kw for kw, v in T.items() if v == vol_q]
        if not candidates:
            continue
        q_prime = random.choice(candidates)
        for e in S_q:
            e_oram_id = e["oram_id"]
            group = oram_groups.get(e_oram_id, [])
            if not group:
                total_tuples += 1
                continue
            chosen_i = random.randrange(len(group))
            chosen_tuple = group.pop(chosen_i)
            if chosen_tuple["keyword"] == q_prime:
                correct += 1
            total_tuples += 1
        T.pop(q_prime, None)
    return correct / total_tuples if total_tuples > 0 else 0.0

def test_path_oram():
    client = Client(num_levels=4, bucket_size=4)
    client.write("a", "apple")
    client.write("b", "banana")
    client.write("c", "cherry")
    client.write("d", "date")
    client.write("e", "elderberry")
    for k in ["a", "b", "c", "d", "e"]:
        client.read(k)

    client.write("c", "coconut")
    client.read("c")
    client.read("z")

    for node_idx in range(1, len(client.server.tree)):
        bucket = client.server.tree[node_idx]
        if bucket is not None:
            for block in bucket.blocks:
                if block.encrypted_data is not None:
                    assert isinstance(block.encrypted_data, bytes), "data should be raw bytes"

def test_seal():
    dataset = {
        "theft": ["doc1", "doc2", "doc3", "doc4", "doc5"],
        "battery": ["doc6", "doc7", "doc8"],
        "robbery": ["doc9"]
    }
    seal = SealClient(alpha=2, dataset=dataset, x=2)

    print(f"Sorted array M: {seal.M}")
    print(f"ODICT: {seal.odict_data}")

    for keyword in ["theft", "battery", "robbery"]:
        seal.clear_access_log()
        results = seal.search(keyword)
        print(f"search({keyword}) = {results}, access_log = {seal.get_access_log()}")

    for oram in seal.orams:
        for node_idx in range(1, len(oram.server.tree)):
            bucket = oram.server.tree[node_idx]
            if bucket is not None:
                for block in bucket.blocks:
                    if block.encrypted_data is not None:
                        assert isinstance(block.encrypted_data, bytes), "SEAL oram data should be raw bytes"


'''
orders = 9
lineitem = 16
customer = 8
part = 9
partsupp = 5
supplier = 7
nation = 4
region = 3
'''

NUM_QUERIES = 100
ALPHA_VALUES = [0, 1, 2, 3, 4]
X_VALUES = [1, 2, 4]
ATTRIBUTE = 3

def test_simulation():
    # load datasets
    crime_freqs = load_crime_frequencies(max_rows=10000)
    orders_tpch_freqs = load_tpch_frequencies("orders", max_rows=10000)[ATTRIBUTE]
    print("finished loading datasets")

    all_results = {}
    for name, keyword_volumes in [("crime", crime_freqs), ("tpch", orders_tpch_freqs)]:
        keywords = [kw for kw in keyword_volumes.keys() if kw != "__dummy_kw__"]
        print(f"\nDataset: {name} ({len(keywords)} keywords, {sum(keyword_volumes.values())} records)")

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
                qr_volumes, qr_tuples, index_to_oram = simulate_seal_access(alpha, M, odict, query_sequence)
                qr_success = query_recovery_attack(padded_volumes, qr_volumes)
                dr_success = database_recovery_attack(padded_volumes, qr_tuples, alpha, index_to_oram)

                key = f"a{alpha}_x{x}"
                results[key] = {
                    "alpha": alpha,
                    "x": x,
                    "query_recovery": qr_success,
                    "database_recovery": dr_success
                }
                print(f"  alpha={alpha}, x={x}: QR={qr_success:.2%}, DR={dr_success:.2%}")

        all_results[name] = results

    with open("results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("results made")

if __name__ == "__main__":
    test_path_oram()
    test_seal()
    test_simulation()
