# word play on buttoning, buttons. and the PTRS anti-tank rifle
# graphics for pretty buttons

import Events

class Button:
    DEFAULT_COLOR = 0xB5B6
    DEFAULT_OUTLINE_COLOR = 0x7BCF
    DEFAULT_TEXT_COLOR = 0xFFFF
    DEFAULT_TEXT_RATIO = 30  #characters per line, 30 for 240x240 screen with 8 pixel large font

    def __init__(self, x, y, w, h, callback = None, name = ""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.name = name
        self.touching = False
        if callback == None:
            self.callback = self.default_callback

    def default_callback(self):
        Kernel.event(ButtonEvent(self))

    def event(self, event):
        if event is Events.ReleaseEvent:
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.callback()
        if event is Events.TouchEvent:
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.touching = True
            else:
                self.touching = False

    def draw(self, buff):
        if self.touching:
            buff.rect(self.x, self.y, self.w, self.h, Button.DEFAULT_OUTLINE_COLOR, True)
            buff.rect(self.x, self.y, self.w, self.h, Button.DEFAULT_COLOR, False)
        else:
            buff.rect(self.x, self.y, self.w, self.h, Button.DEFAULT_COLOR, True)
            buff.rect(self.x, self.y, self.w, self.h, Button.DEFAULT_OUTLINE_COLOR, False)
        textlen = float(len(self.name))
        if textlen > 0.0:
            tx = self.x + self.w / 2.0 - (1.0/Button.DEFAULT_TEXT_RATIO * textlen / 2.0)
            ty = self.y + self.h / 2.0
            buff.text(self.name, tx, ty, Button.DEFAULT_TEXT_COLOR)

