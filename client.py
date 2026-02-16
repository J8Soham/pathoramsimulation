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
        self.initialize_server()

    def initialize_server(self):
        dummy_block = {"key": "", "value": "", "is_dummy": True}
        for node_idx in range(1, len(self.server.tree)):
            encrypted_dummy = self._encrypt_block(dummy_block)
            bucket = self.server.tree[node_idx]
            for block in bucket.blocks:
                block.encrypted_data = encrypted_dummy

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
                if not decrypted["is_dummy"]: # ignore dummy
                    existing = next((s for s in self.stash if s["key"] == decrypted["key"]), None)
                    if existing is None:
                        self.stash.append(decrypted)
    
    def _add_to_bucket(self, index, bucket, block):
        for i in range(self.bucket_size):
            decrypted = self._decrypt_block(bucket.blocks[i].encrypted_data)
            if decrypted["is_dummy"]:
                bucket.blocks[i].encrypted_data = self._encrypt_block(block)
                self.server.write_bucket(index, bucket)
                return True
        return False
    
    def _write_back(self, leaf):
        path = self._get_path(leaf)
        encrypted_buckets = []
        for node in range(len(path)):
            bucket_data = []
            filled = 0
            remaining_stash = []
            for block in self.stash:
                if filled < (self.bucket_size * self.num_levels):
                    block_leaf = self.position_map.get(block["key"])
                    block_path = self._get_path(block_leaf)
                    if path[node] in block_path:
                        see_these = block_path[node:]
                        old_filled = filled
                        for element in see_these:
                            bucket = self.server.get_bucket(element)
                            can_add = self._add_to_bucket(element, bucket, self._encrypt_block(block))
                            if can_add:
                                filled += 1
                                break
                        if filled == old_filled:
                            remaining_stash.append(block)    
                        if (filled - old_filled > 1):
                            print("Error: added twice")
                else:
                    remaining_stash.append(block)
            self.stash = remaining_stash
        
        while filled < (self.bucket_size * self.num_levels):
            dummy = {"key": "", "value": "", "is_dummy": True}
            random_bucket = path[random.randint(0, len(path) - 1)]
            can_add = self._add_to_bucket(random_bucket, self._encrypt_block(dummy))
            if can_add:
                filled += 1

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
        leaf_for_adding = old_leaf if old_leaf is not None else new_leaf

        self._retrieve_from_server(leaf_for_adding) # get things from server

        existing_in_stash = next((s for s in self.stash if s["key"] == key), None)
        if existing_in_stash:
            existing_in_stash["value"] = value
        else:
            self.stash.append({"key": key, "value": value, "is_dummy": False})

        self._write_back(leaf_for_adding)  # put things back to server
        print(f"write({key}) = {value}")
        return value
