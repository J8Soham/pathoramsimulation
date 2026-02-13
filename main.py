from client import Client

def main():
    client = Client(num_levels=4, bucket_size=4)
    client.write("a", "apple")
    client.write("b", "banana")
    client.write("c", "cherry")
    client.write("d", "date")
    client.write("e", "elderberry")
    for k in ["a", "b", "c", "d", "e"]:
        print(f"read({k}) = {client.read(k)}")

    client.write("c", "coconut")
    print(f"read(c) = {client.read('c')}")
    print(f"read(z) = {client.read('z')}")

    for node_idx in range(1, len(client.server.tree)):
        bucket = client.server.tree[node_idx]
        if bucket is not None:
            for block in bucket.blocks:
                if block.encrypted_data is not None:
                    assert isinstance(block.encrypted_data, bytes), "data should be raw bytes"

if __name__ == "__main__":
    main()
