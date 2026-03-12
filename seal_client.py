import os
import math
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from client import Client
from utils import adj_padding

class SealClient:
    def __init__(self, alpha, dataset, x=1, bucket_size=4):
        self.alpha = alpha # number of bits leaked
        self.x = x # padding 
        self.num_orams = 1 << alpha
        self.bucket_size = bucket_size
        self.prp_key = AESGCM.generate_key(bit_length=128)
        self.prp = AESGCM(self.prp_key)
        self.access_log = []

        padded_dataset = adj_padding(dataset, x)

        self.M = []
        for keyword in sorted(padded_dataset.keys()):
            for doc_id in padded_dataset[keyword]:
                self.M.append((keyword, doc_id))
        N = len(self.M)

        self.odict_data = {}
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

        items_per_oram = max(1, N // self.num_orams) if self.num_orams > 0 else N
        num_levels = max(2, math.ceil(math.log2(max(items_per_oram, 2))) + 1)
        self.orams = [Client(num_levels, bucket_size) for _ in range(self.num_orams)]

        odict_levels = max(2, math.ceil(math.log2(max(len(padded_dataset), 2))) + 1)
        self.odict_oram = Client(odict_levels, bucket_size)

        for keyword, (start_idx, cnt) in self.odict_data.items():
            self.odict_oram.write(keyword, json.dumps({"i": start_idx, "c": cnt}))

        for i, (kw, doc_id) in enumerate(self.M):
            value = doc_id if doc_id is not None else ""
            oram_idx = self._prp_to_oram(i)
            self.orams[oram_idx].write(str(i), value)

    def _prp_to_oram(self, index):
        padded = str(index).encode().ljust(16, b'\x00')[:16]
        nonce = b'\x00' * 12
        encrypted = self.prp.encrypt(nonce, padded, None)
        if self.alpha == 0:
            return 0
        return encrypted[0] % self.num_orams

    def search(self, keyword):
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
