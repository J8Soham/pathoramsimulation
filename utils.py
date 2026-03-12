import math
import random
from collections import Counter


def adj_padding(dataset, x):
    if x <= 1:
        return dataset
    N = sum(len(docs) for docs in dataset.values())
    padded = {}
    for keyword, doc_ids in dataset.items():
        count = len(doc_ids)
        padded_count = 1
        while padded_count < count:
            padded_count *= x
        dummy_count = padded_count - count
        padded[keyword] = list(doc_ids) + [None] * dummy_count
    padded_total = sum(len(docs) for docs in padded.values())
    target_total = x * N
    if padded_total < target_total:
        extra = target_total - padded_total
        padded["__dummy_kw__"] = [None] * extra
    return padded


def adj_padding_volumes(keyword_volumes, x):
    if x <= 1:
        return dict(keyword_volumes)
    N = sum(keyword_volumes.values())
    padded = {}
    for kw, count in keyword_volumes.items():
        padded_count = 1
        while padded_count < count:
            padded_count *= x
        padded[kw] = padded_count
    padded_total = sum(padded.values())
    target_total = x * N
    if padded_total < target_total:
        padded["__dummy_kw__"] = target_total - padded_total
    return padded


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


def database_recovery_attack(padded_volumes, queries_with_tuples, alpha):
    num_orams = 1 << alpha
    oram_groups = {}
    idx = 0
    for kw in sorted(padded_volumes.keys()):
        vol = padded_volumes[kw]
        for _ in range(vol):
            oram_id = idx % num_orams if alpha > 0 else 0
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
