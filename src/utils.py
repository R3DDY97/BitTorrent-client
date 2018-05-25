#!/usr/bin/env python3


def is_magneturl(torrent):
    prefixes = ["magnet:", "http://", "https://"]
    for prefix in prefixes:
        if torrent.startswith(prefix):
            return True
    return False


def b2kb(size):
    kb = size / 10**3
    return "{:.2f}KB".format(kb)


def b2mb(size):
    mb = size / 10**6
    return "{:.2f}MB".format(mb)
