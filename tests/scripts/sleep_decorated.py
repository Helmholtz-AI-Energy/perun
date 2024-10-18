import random
import time

import perun


@perun.perun()
def sleep(value):
    time.sleep(10)
    return value


if __name__ == "__main__":
    value = random.randint(0, 100)
    result = sleep(value)
    assert result == value
