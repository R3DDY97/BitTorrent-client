#!/usr/bin/env python3

# Copyright Daniel Wallin 2006. Use, modification and distribution is
# subject to the Boost Software License, Version 1.0. (See accompanying
# file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)


import time
import msvcrt
import Console


class WindowsConsole:
    def __init__(self):

        self.console = Console.getconsole()

    def clear(self):
        self.console.page()

    def write(self, str):
        self.console.write(str)

    def sleep_and_input(self, seconds):
        time.sleep(seconds)
        if msvcrt.kbhit():
            return msvcrt.getch()
        return None
