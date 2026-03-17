import math
import random
from collections import Counter
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

'''
ADJ-Padding-Volumes(x, D) from SEAL 
same as adj_padding but only for counts (not for individual docs)
'''
def adj_padding_volumes(keyword_volumes, x):
    # case for no padding
    if x <= 1:
        return dict(keyword_volumes)
    # otherwise
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

'''
builds sorted array M and ODICT from keyword volumes, 
where M is array of (keyword, doc_id) pairs sorted lexicographically by keyword
and ODICT maps each keyword to (start_index, count) in M
'''
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

''' 
simulating seal cause it runs slow by
1. abstracting files to counts, 
2. asking just for range of indices,
3. using prp to determine which oram each index maps to a query
still returning query_results_volumes and query_results_tuples for the attacks 
'''
def simulate_seal_access(alpha, M, odict, query_sequence):
    prp_key = AESGCM.generate_key(bit_length=128)
    prp = AESGCM(prp_key)
    num_orams = 1 << alpha

    index_to_oram = {}
    for i in range(len(M)):
        index_to_oram[i] = prp_to_oram(prp, alpha, num_orams, i)

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

    return query_results_volumes, query_results_tuples, index_to_oram

def prp_to_oram(prp, alpha, num_orams, index):
    padded = str(index).encode().ljust(16, b'\x00')[:16]
    nonce = b'\x00' * 12
    encrypted = prp.encrypt(nonce, padded, None)
    if alpha == 0:
        return 0
    return encrypted[0] % num_orams