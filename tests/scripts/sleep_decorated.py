import time

import perun


@perun.perun()
def sleep():
    time.sleep(10)


if __name__ == "__main__":
    sleep()
