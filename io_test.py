import time
data = b"x" * (5 * 1024 * 1024)
with open("bigfile.bin", "wb") as f:
    for _ in range(5):
        f.write(data)
        f.flush()
        import os
        os.fsync(f.fileno())
        time.sleep(0.5)
time.sleep(1)
