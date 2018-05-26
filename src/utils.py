#!/usr/bin/env python3


def is_magneturl(torrent):
    prefixes = ["magnet:", "http://", "https://"]
    for prefix in prefixes:
        if torrent.startswith(prefix):
            return True
    return False


def rate_size(size):
    if size < 10**6:
        rsize = size / 10**3
        return "{:.2f}KB/s".format(rsize)
    rsize = size / 10**6
    return "{:.2f}MB/s".format(rsize)


def b2kmg(size):
    if size < 10**6:
        mb = size / 10**3
        return "{:.2f}KB".format(mb)
    elif size > 10**6 and size < 10**9:
        mb = size / 10 ** 6
        return "{:.2f}MB".format(mb)
    elif size > 10 ** 9:
        mb = size / 10 ** 9
        return "{:.2f}GB".format(mb)
