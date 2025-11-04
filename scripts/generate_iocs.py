#!/usr/bin/env python3
import random, hashlib
print({"hashes": [hashlib.sha256(str(random.random()).encode()).hexdigest() for _ in range(3)]})
