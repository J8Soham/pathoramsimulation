import random
import json
import matplotlib.pyplot as plt
from client import Client
from client_seal import SealClient
from load_data import load_crime_frequencies, load_tpch_frequencies, load_apartments_frequencies
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

def extract_trace_from_actual_seal(seal, query_sequence):
    query_results_volumes = []
    query_results_tuples = []
    
    index_to_oram = {}
    for i in range(len(seal.M)):
        index_to_oram[i] = seal._prp_to_oram(i)
        
    for kw in query_sequence:
        if kw not in seal.odict_data:
            continue
        seal.clear_access_log()
        _ = seal.search(kw)
        access_log = seal.get_access_log()
        
        i_w, cnt_w = seal.odict_data[kw]
        
        tuples = []
        for idx_offset, oram_id in enumerate(access_log):
            i = i_w + idx_offset
            tuples.append({"oram_id": oram_id, "index": i})
            
        query_results_volumes.append((kw, cnt_w))
        query_results_tuples.append((kw, tuples))
        
    return query_results_volumes, query_results_tuples, index_to_oram

def test_simulation_equivalence(num_of_queries, attribute):
    apartments_freqs = load_apartments_frequencies(max_rows=10000) # liteeraly the max
    
    dataset = {}
    doc_idx = 0
    for kw, count in apartments_freqs.items():
        if kw == "__dummy_kw__": continue
        dataset[kw] = [f"doc_{doc_idx + i}" for i in range(count)]
        doc_idx += count
        
    x = 2
    alpha = 2
    
    print("Initializing SEAL")
    seal = SealClient(alpha=alpha, dataset=dataset, x=x)
    
    keyword_volumes = {k: len(v) for k, v in dataset.items()}
    padded_volumes = adj_padding_volumes(keyword_volumes, x)
    M, odict = build_sorted_array(padded_volumes)
    
    keywords = list(keyword_volumes.keys())
    query_sequence = random.choices(
        keywords,
        weights=[keyword_volumes[kw] for kw in keywords],
        k=num_of_queries
    )
    
    print("Getting both of them set up lol no error till here")
    qr_vol_sim, qr_tup_sim, idx_to_oram_sim = simulate_seal_access(alpha, M, odict, query_sequence)
    qr_vol_actual, qr_tup_actual, idx_to_oram_actual = extract_trace_from_actual_seal(seal, query_sequence)
    padded_actual = {kw: len(docs) for kw, docs in seal._adj_padding(dataset, x).items()}

    dr_success_sim = database_recovery_attack(padded_volumes, qr_tup_sim, alpha, idx_to_oram_sim)
    dr_success_actual = database_recovery_attack(padded_actual, qr_tup_actual, alpha, idx_to_oram_actual)
    
    qr_success_sim = query_recovery_attack(padded_volumes, qr_vol_sim)
    qr_success_actual = query_recovery_attack(padded_actual, qr_vol_actual)
    
    print(f"Simulation DR Success: {dr_success_sim:.10%}")
    print(f"Actual SEAL DR Success: {dr_success_actual:.10%}")
    print(f"Simulation QR Success: {qr_success_sim:.10%}")
    print(f"Actual SEAL QR Success: {qr_success_actual:.10%}")
    return dr_success_sim, dr_success_actual, qr_success_sim, qr_success_actual

ALPHA_VALUES = [0, 4, 8, 12, 16, 20, 24]
X_VALUES = [1, 2, 4, 8, 16, 32, 64]
NUM_QUERIES = 1000
ATTRIBUTE = 5

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

        all_results[name] = {
            "results": results,
            "random_baseline": 1.0 / len(keywords) if keywords else 0,
            "greedy_baseline": max(keyword_volumes[kw] for kw in keywords) / sum(keyword_volumes[kw] for kw in keywords) if keywords else 0
        }

    with open("results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    for metric_name, metric_key in [("Query Recovery", "query_recovery"), ("Database Recovery", "database_recovery")]:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        for i, (name, title) in enumerate([("crime", "Crime Dataset"), ("tpch", "TPC-H Orders Dataset")]):
            ax = axes[i]
            if name not in all_results:
                continue
                
            dataset_data = all_results[name]
            results_dict = dataset_data["results"]
            
            if metric_key == "query_recovery":
                y_values = []
                for x in X_VALUES:
                    key = f"a{ALPHA_VALUES[0]}_x{x}"
                    if key in results_dict:
                        y_values.append(results_dict[key][metric_key] * 100)
                ax.plot(X_VALUES[:len(y_values)], y_values, marker='o', label="Attack Success Rate")
                ax.set_xlabel("x (Padding parameter)")
                
                baseline = dataset_data["random_baseline"] * 100
                ax.axhline(y=baseline, color='black', linestyle='--', linewidth=2, label='Random Strategy Base')
            else:
                for x in X_VALUES:
                    y_values = []
                    for alpha in ALPHA_VALUES:
                        key = f"a{alpha}_x{x}"
                        if key in results_dict:
                            y_values.append(results_dict[key][metric_key] * 100)
                    ax.plot(ALPHA_VALUES[:len(y_values)], y_values, marker='o', label=f"x={x}")
                ax.set_xlabel("Alpha (bits)")
                
                baseline = dataset_data["greedy_baseline"] * 100
                ax.axhline(y=baseline, color='black', linestyle='--', linewidth=2, label='Greedy Strategy Base')
                
            ax.set_ylabel(f"{metric_name} Success Rate (%)")
            ax.set_title(title)
            ax.legend()
            ax.grid(True)
            
        plt.tight_layout()
        plt.savefig(f"{metric_key}_plot.png")

if __name__ == "__main__":
    # test_path_oram()
    # test_seal()
    test_simulation()

    # comment this out to remove the simulation equivalence test - should probably put this in a function. 
    # dr_sim_results = []
    # dr_act_results = []
    # qr_sim_results = []
    # qr_act_results = []
    # list_of_queries = [10, 100, 1000, 10000]
    # for queries in list_of_queries:
    #     dr_sim, dr_act, qr_sim, qr_act = test_simulation_equivalence(queries, 3)
    #     dr_sim_results.append(dr_sim)
    #     dr_act_results.append(dr_act)
    #     qr_sim_results.append(qr_sim)
    #     qr_act_results.append(qr_act)

    # plt.figure(figsize=(10, 6))
    # plt.plot(list_of_queries, dr_sim_results, label='Simulation DR', marker='o', linestyle='-', color='blue')
    # plt.plot(list_of_queries, dr_act_results, label='Actual SEAL DR', marker='x', linestyle='--', color='lightblue')
    
    # plt.plot(list_of_queries, qr_sim_results, label='Simulation QR', marker='s', linestyle='-', color='red')
    # plt.plot(list_of_queries, qr_act_results, label='Actual SEAL QR', marker='d', linestyle='--', color='lightcoral')
    
    # plt.xscale('log')
    # plt.xlabel('Number of Queries')
    # plt.ylabel('Attack Success Rate')
    # plt.title('Convergence of Database and Query Recovery Attacks')
    # plt.legend()
    # plt.grid(True)
    # plt.savefig('convergence_plot.png')
