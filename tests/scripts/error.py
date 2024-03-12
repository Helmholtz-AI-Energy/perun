import time

time.sleep(5)

with open("does-not-exist.txt", "r") as file:
    lines = file.readlines()
    for line in lines:
        print(line)

time.sleep(5)
