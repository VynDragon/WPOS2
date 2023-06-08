#
# SPDX-FileCopyrightText: 2023  <mail@massdriver.space>
# SPDX-License-Identifier: Apache-2.0
#

import framebuf

class WPFrameBuffer(framebuf.FrameBuffer):
    def __init__(self, buffer, width, height, format, stride = None):
        if stride == None:
            super().__init__(buffer, width, height, format, width)
        else:
            super().__init__(buffer, width, height, format, stride)
        self.width = width
        self.height = height
        self.maxX = None
        self.maxY = None
        self.minX = None
        self.minY = None

    def update_max(self, x, y):
        if self.maxX == None:
           self.maxX = x
        else:
            self.maxX = max(x, self.maxX)
        if self.maxY == None:
           self.maxY = y
        else:
            self.maxY = max(y, self.maxY)
        if self.minX == None:
           self.minX = x
        else:
            self.minX = min(x, self.minX)
        if self.minY == None:
           self.minY = y
        else:
            self.minY = min(y, self.minY)

    def clear_max():
        self.maxX = None
        self.maxY = None
        self.minX = None
        self.minY = None

    def pixel(self, x, y, c):
        self.update_max(x, y)
        super().pixel(int(x * self.width), int(y * self.height), c)

    def hline(self, x, y, w, c):
        self.update_max(x, y)
        self.update_max(x+w, y)
        super().hline(int(x * self.width), int(y * self.height), int(w * self.width), c)

    def vline(self, x, y, h, c):
        self.update_max(x, y)
        self.update_max(x, y+h)
        super().vline(int(x * self.width), int(y * self.height), int(h * self.height), c)

    def line(self, x1, y1, x2, y2, c):
        self.update_max(x1, y1)
        self.update_max(x2, y2)
        super().line(int(x1 * self.width), int(y1 * self.height), int(x2 * self.width), int(y2 * self.height), c)

    def rect(self, x, y, w, h, c, f = False):
        self.update_max(x, y)
        self.update_max(x + w, y + h)
        super().rect(int(x * self.width), int(y * self.height), int(w * self.width), int(h * self.height), c, f)

    def text(self, s, x, y, c):
        self.update_max(x, y)
        self.update_max(x + 8 * len(s), y+8)
        super().text(s, int(x * self.width), int(y * self.height), c)

    def blit(self, fbuf, x, y, key=-1, palette = None):
        self.update_max(x, y)
        self.update_max(x + fbuf.width, y  + fbuf.height)
        super().blit(fbuf, int(x * self.width), int(y * self.height), key, palette)
