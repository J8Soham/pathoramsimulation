import math

class Block:
    def __init__(self, encrypted_data=None):
        self.encrypted_data = encrypted_data
class Bucket:
    def __init__(self, uid, bucket_size):
        self.uid = uid
        self.blocks = [Block() for _ in range(bucket_size)]

class Server:
    def __init__(self, num_levels, bucket_size=4):
        self.num_levels = num_levels
        self.bucket_size = bucket_size
        self.num_nodes = (1 << num_levels) - 1
        self.tree = [None] + [Bucket(i, bucket_size) for i in range(1, self.num_nodes + 1)]

    def traverse_path(self, leaf):
        path = []
        node = leaf
        while node >= 1:
            path.append(self.tree[node])
            node //= 2
        return path

    def evict(self, leaf, encrypted_buckets): # use the position map info to write it back correctly. 
        node = leaf
        for bucket_data in encrypted_buckets:
            for i, enc_block in enumerate(bucket_data):
                self.tree[node].blocks[i].encrypted_data = enc_block
            node //= 2

