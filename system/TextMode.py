import st7789
import vga1_8x8

class TextMode_st7789:
    _lines = 30
    _line_offset = 8
    _rows = 30
    _rows_offset = 8

    def __init__(self, display):
        self.display = display
        self.lines = []

    def print(self, text):
        texts = text.split("\n")
        for tex in texts:
            self.print_noreturns(tex)

    def print_noreturns(self, text):
        while len(text) > self._rows:
            text2 = text[:self._rows]
            self.lines.append(text2)
            if len(self.lines) > self._lines:
                self.force_redraw()
            else:
                self.display.text(vga1_8x8, text2, 0, (len(self.lines) - 1) * self._line_offset)
            text = text[self._rows:]
        self.lines.append(text)
        if len(self.lines) > self._lines:
            self.force_redraw()
        else:
            self.display.text(vga1_8x8, text, 0, (len(self.lines) - 1) * self._line_offset)
    def force_redraw(self):
        self.display.fill(st7789.BLACK)
        if len(self.lines) > self._lines:
            self.lines = self.lines[-self._lines:]
        for id, line in enumerate(self.lines):
            self.display.text(vga1_8x8, line, 0, id * self._line_offset)
