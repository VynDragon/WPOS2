#
# SPDX-FileCopyrightText: 2023  <mail@massdriver.space>
# SPDX-License-Identifier: Apache-2.0
#

import framebuf, writer, Single

class WPPalette(framebuf.FrameBuffer):
    def __init__(self):
        buf = bytearray(4)
        buf[0] = 0
        buf[1] = 0
        buf[2] = 0xFF
        buf[3] = 0xFF
        super().__init__(buf, 2, 1, framebuf.RGB565)

    def fg(self, color):  # Set foreground color
        self.pixel(1, 0, color)

    def bg(self, color):
        self.pixel(0, 0, color)

class WriterFrameBuffer(framebuf.FrameBuffer):
    def __init__(self, buffer, width, height, format, stride = None):
        if stride == None:
            super().__init__(buffer, width, height, format, width)
        else:
            super().__init__(buffer, width, height, format, stride)
        self.width = width
        self.height = height
        self.palette = WPPalette()

class FrameBuffer(framebuf.FrameBuffer):
    def __init__(self, buffer, width, height, format, stride = None):
        if stride == None:
            super().__init__(buffer, width, height, format, width)
        else:
            super().__init__(buffer, width, height, format, stride)
        self.width = width
        self.height = height
        self.buffer = buffer


class WPFrameBuffer(FrameBuffer):
    def __init__(self, buffer, width, height, format, stride = None):
        if stride == None:
            super().__init__(buffer, width, height, format, width)
        else:
            super().__init__(buffer, width, height, format, stride)
        self.maxX = None
        self.maxY = None
        self.minX = None
        self.minY = None
        self.palette = WPPalette()
        self.fb = WriterFrameBuffer(buffer, width, height, framebuf.RGB565) # regular framebuffer backed by same buffer for high performance access (with no floats but requires device awareness)

    @micropython.native
    def update_max(self, x: int, y: int) -> None:
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

    @micropython.native
    def clear_max(self):
        self.maxX = None
        self.maxY = None
        self.minX = None
        self.minY = None

    @micropython.native
    def pixel(self, x, y, c):
        rx = int(x * self.width)
        ry = int(y * self.height)
        self.update_max(rx, ry)
        super().pixel(rx, ry, c)

    @micropython.native
    def hline(self, x, y, w, c):
        rx = int(x * self.width)
        ry = int(y * self.height)
        rw = int(w * self.width)
        self.update_max(rx, ry)
        self.update_max(rx+rw, ry)
        super().hline(rx, ry, rw, c)

    @micropython.native
    def vline(self, x, y, h, c):
        rx = int(x * self.width)
        ry = int(y * self.height)
        rh = int(h * self.height)
        self.update_max(rx, ry)
        self.update_max(rx, ry+rh)
        super().vline(rx, ry, rh, c)

    @micropython.native
    def line(self, x1, y1, x2, y2, c):
        rx1 = int(x1 * self.width)
        ry1 = int(y1 * self.height)
        rx2 = int(x2 * self.width)
        ry2 = int(y2 * self.height)
        self.update_max(rx1, ry1)
        self.update_max(rx2, ry2)
        super().line(rx1, ry1, rx2, ry2, c)

    @micropython.native
    def rect(self, x, y, w, h, c, f = False):
        rx = int(x * self.width)
        ry = int(y * self.height)
        rw = int(w * self.width)
        rh = int(h * self.height)
        self.update_max(rx, ry)
        self.update_max(rx + rw, ry + rh)
        super().rect(rx, ry, rw, rh, c, f)

    @micropython.native
    def ellipse(self, x, y, w, h, c, f = False):
        rx = int(x * self.width)
        ry = int(y * self.height)
        rw = int(w * self.width)
        rh = int(h * self.height)
        self.update_max(rx - rw / 2, ry - rw / 2)
        self.update_max(rx + rw / 2, ry + rh / 2)
        super().ellipse(rx, ry, rw, rh, c, f)

    @micropython.native
    def text(self, s, x, y, c):
        rx = int(x * self.width)
        ry = int(y * self.height)
        self.update_max(rx, ry)
        self.update_max(rx + 8 * len(s), ry + 8)
        super().text(s, rx, ry, c)

    @micropython.native
    def text2(self, s, x, y, font):
        rx = int(x * self.width)
        ry = int(y * self.height)
        self.update_max(rx, ry)
        monospace_size = font.height()
        self.update_max(rx + monospace_size * len(s), ry + monospace_size)
        the_writer = writer.CWriter(self.fb , font, Single.DEFAULT_TEXT_COLOR, Single.DEFAULT_BG_COLOR, False)
        the_writer.set_textpos(self.fb, ry, rx) # ?? different x y order than other fucntions?
        the_writer.printstring(s)

    @micropython.native
    def blit(self, fbuf: FrameBuffer, x, y, key=-1, palette = None):
        rx = int(x * self.width)
        ry = int(y * self.height)
        self.update_max(rx, ry)
        self.update_max(rx + fbuf.width, ry + fbuf.height)
        super().blit(fbuf, rx, ry, key, palette)
