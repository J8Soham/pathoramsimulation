import os
import json
import random
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from server import Server

class Client:
    def __init__(self, num_levels, bucket_size=4):
        self.num_levels = num_levels
        self.bucket_size = bucket_size
        self.num_leaves = 1 << (num_levels - 1)
        
        self.server = Server(num_levels, bucket_size)
        self.position_map = {}
        self.stash = []
        self.key = AESGCM.generate_key(bit_length=128)
        self.aes = AESGCM(self.key)

    def _encrypt_block(self, block): # this is CPA secure
        plaintext = json.dumps(block).encode()
        nonce = os.urandom(12)
        ciphertext = self.aes.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def _decrypt_block(self, data): # this is CPA secure
        if data is None:
            return None
        nonce = data[:12]
        ciphertext = data[12:]
        plaintext = self.aes.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode())

    def _get_path(self, leaf): # https://www.geeksforgeeks.org/dsa/array-representation-of-binary-heap/
        path = []
        node = leaf
        while node >= 1:
            path.append(node)
            node //= 2
        return path

    def _random_leaf(self):
        return random.randint(self.num_leaves, self.num_leaves + self.num_leaves - 1)

    def _retrieve_from_server(self, leaf):
        buckets = self.server.traverse_path(leaf)
        for bucket in buckets:
            for block in bucket.blocks:
                decrypted = self._decrypt_block(block.encrypted_data)
                if decrypted is not None and not decrypted["is_dummy"]: # ignore dummy and empty blocks
                    existing = next((s for s in self.stash if s["key"] == decrypted["key"]), None)
                    if existing is None:
                        self.stash.append(decrypted)

    def _write_back(self, leaf):
        path = self._get_path(leaf)
        encrypted_buckets = []
        for node in path:
            bucket_data = []
            filled = 0
            remaining_stash = []
            for block in self.stash:
                if filled < self.bucket_size:
                    block_leaf = self.position_map.get(block["key"])
                    if block_leaf is not None:
                        block_path = self._get_path(block_leaf)
                        if node in block_path:
                            bucket_data.append(self._encrypt_block(block))
                            filled += 1
                            continue
                remaining_stash.append(block)
            self.stash = remaining_stash
            while filled < self.bucket_size:
                dummy = {"key": "", "value": "", "is_dummy": True}
                bucket_data.append(self._encrypt_block(dummy))
                filled += 1
            encrypted_buckets.append(bucket_data)
        self.server.evict(leaf, encrypted_buckets)

    def read(self, key):
        if key not in self.position_map:
            return None
        leaf = self.position_map[key]
        self._retrieve_from_server(leaf) # get things from server

        result = None
        for block in self.stash:
            if block["key"] == key:
                result = block["value"]
                break
        self.position_map[key] = self._random_leaf()

        self._write_back(leaf) # put things back to server
        print(f"read({key}) = {result}")
        return result

    def write(self, key, value):
        old_leaf = self.position_map.get(key)
        new_leaf = self._random_leaf()
        self.position_map[key] = new_leaf
        leaf_for_eviction = old_leaf if old_leaf is not None else new_leaf

        self._retrieve_from_server(leaf_for_eviction) # get things from server

        existing_in_stash = next((s for s in self.stash if s["key"] == key), None)
        if existing_in_stash:
            existing_in_stash["value"] = value
        else:
            self.stash.append({"key": key, "value": value, "is_dummy": False})

        self._write_back(leaf_for_eviction)  # put things back to server
        print(f"write({key}) = {value}")
        return value
