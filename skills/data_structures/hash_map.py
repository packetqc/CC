"""Hash Map - Key-value storage with O(1) average access.

A hash map uses a hash function to map keys to bucket indices,
providing near-constant time lookups, insertions, and deletions.

Key concepts:
- Hash function: converts keys to array indices
- Collision handling: chaining (linked lists) or open addressing
- Load factor: ratio of entries to buckets; triggers resize when high
"""


class HashMap:
    def __init__(self, capacity=16):
        self.capacity = capacity
        self.size = 0
        self.buckets = [[] for _ in range(capacity)]
        self.load_factor_threshold = 0.75

    def _hash(self, key):
        """Compute bucket index for a key."""
        return hash(key) % self.capacity

    def put(self, key, value):
        """Insert or update a key-value pair. Amortized O(1)."""
        idx = self._hash(key)
        bucket = self.buckets[idx]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self.size += 1
        if self.size / self.capacity > self.load_factor_threshold:
            self._resize()

    def get(self, key, default=None):
        """Retrieve a value by key. O(1) average."""
        idx = self._hash(key)
        for k, v in self.buckets[idx]:
            if k == key:
                return v
        return default

    def delete(self, key):
        """Remove a key-value pair. O(1) average."""
        idx = self._hash(key)
        bucket = self.buckets[idx]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket.pop(i)
                self.size -= 1
                return True
        return False

    def _resize(self):
        """Double capacity and rehash all entries."""
        old_buckets = self.buckets
        self.capacity *= 2
        self.buckets = [[] for _ in range(self.capacity)]
        self.size = 0
        for bucket in old_buckets:
            for key, value in bucket:
                self.put(key, value)

    def keys(self):
        """Return all keys."""
        return [k for bucket in self.buckets for k, v in bucket]

    def values(self):
        """Return all values."""
        return [v for bucket in self.buckets for k, v in bucket]

    def __len__(self):
        return self.size

    def __contains__(self, key):
        return self.get(key, sentinel := object()) is not sentinel

    def __repr__(self):
        items = [(k, v) for bucket in self.buckets for k, v in bucket]
        return f"HashMap({dict(items)})"
