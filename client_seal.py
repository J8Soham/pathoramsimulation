import os
import math
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from client import Client

class SealClient:
    def __init__(self, alpha, dataset, x=1, bucket_size=4):
        '''
        1. intializes variable
        2. pads the dataset
        3. creates sorted array M
        4. creates ODICT and then write
        5. creates ORAMs and then write
        '''
        self.alpha = alpha
        self.x = x
        self.num_orams = 1 << alpha
        self.bucket_size = bucket_size
        self.prp_key = AESGCM.generate_key(bit_length=128)
        self.prp = AESGCM(self.prp_key)
        self.access_log = []

        padded_dataset = self._adj_padding(dataset, x)

        self.M = [] # step 3
        for keyword in sorted(padded_dataset.keys()):
            for doc_id in padded_dataset[keyword]:
                self.M.append((keyword, doc_id))
        N = len(self.M)

        self.odict_data = {} # step 4
        current_keyword = None 
        start_idx = 0
        for i, (kw, _) in enumerate(self.M):
            if kw != current_keyword:
                if current_keyword is not None:
                    self.odict_data[current_keyword] = (start_idx, i - start_idx)
                current_keyword = kw
                start_idx = i
        if current_keyword is not None:
            self.odict_data[current_keyword] = (start_idx, N - start_idx)

        odict_levels = max(2, math.ceil(math.log2(max(len(padded_dataset), 2))) + 1)
        self.odict_oram = Client(odict_levels, bucket_size)

        for keyword, (start_idx, cnt) in self.odict_data.items(): # odict add
            self.odict_oram.write(keyword, json.dumps({"i": start_idx, "c": cnt}))

        items_per_oram = max(1, N // self.num_orams) if self.num_orams > 0 else N
        num_levels = max(2, math.ceil(math.log2(max(items_per_oram, 2))) + 1)
        self.orams = [Client(num_levels, bucket_size) for _ in range(self.num_orams)] # step 5

        for i, (kw, doc_id) in enumerate(self.M): # oram add
            value = doc_id if doc_id is not None else ""
            oram_idx = self._prp_to_oram(i)
            self.orams[oram_idx].write(str(i), value)

    def _adj_padding(self, dataset, x):
        '''
        ADJ-Padding(x, D) from SEAL 
        basically we want to pad each keyword's document list to 2^x 
        along with paddding dataset size to x * N (return this dataset for compute)
        '''
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

    def _prp_to_oram(self, index):
        '''
        Basically we want to map each index to an oram id so that we can recreate it anytimes
        this means it has to be deterministic 
        doesn't affect the security cause it can be know by adversary (see Database recovery attack which literally gets passed the index_to_oram)
        '''
        padded = str(index).encode().ljust(16, b'\x00')[:16]
        nonce = b'\x00' * 12
        encrypted = self.prp.encrypt(nonce, padded, None)
        if self.alpha == 0:
            return 0
        return encrypted[0] & (self.num_orams - 1) # small optimization see https://stackoverflow.com/questions/5454574/how-do-computers-find-modulus

    def search(self, keyword):
        '''
        Basically performs the reads from the ORAM 
        ODICT serves as which index range to read from the ORAM
        '''
        odict_result = self.odict_oram.read(keyword)
        if odict_result is None:
            return []
        parsed = json.loads(odict_result)
        i_w = parsed["i"]
        cnt_w = parsed["c"]

        results = []
        for i in range(i_w, i_w + cnt_w):
            oram_idx = self._prp_to_oram(i)
            self.access_log.append(oram_idx)
            value = self.orams[oram_idx].read(str(i))
            results.append(value)
        return results

    def get_access_log(self):
        return list(self.access_log)

    def clear_access_log(self):
        self.access_log = []
