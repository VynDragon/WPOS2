# word play on buttoning, buttons. and the PTRS anti-tank rifle
# graphics for pretty buttons

import Events
import Single

class Button:
    DEFAULT_COLOR = 0xB5B6
    DEFAULT_OUTLINE_COLOR = 0x7BCF
    DEFAULT_TEXT_COLOR = 0xFFFF
    DEFAULT_TEXT_RATIO = 30  #characters per line, 30 for 240x240 screen with 8 pixel large font
    TOUCH_LAST = 10 # 10 frames

    def __init__(self, x, y, w, h, callback = None, name = ""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.name = name
        self.touching = False
        self.touching_timeout = 0
        self.callback = callback
        if callback == None:
            self.callback = self.default_callback

    def default_callback(self):
        Single.Kernel.event(ButtonEvent(self))

    @micropython.native
    def event(self, event):
        if isinstance(event, Events.ReleaseEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.callback()
            self.touching = False
        if isinstance(event, Events.TouchEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.touching = True
                self.touching_timeout = 0
            else:
                self.touching = False

    @micropython.native
    def draw(self, buff):
        if self.touching and self.touching_timeout < Button.TOUCH_LAST:
            buff.rect(self.x, self.y, self.w, self.h, Button.DEFAULT_OUTLINE_COLOR, True)
            buff.rect(self.x, self.y, self.w, self.h, Button.DEFAULT_COLOR, False)
        else:
            buff.rect(self.x, self.y, self.w, self.h, Button.DEFAULT_COLOR, True)
            buff.rect(self.x, self.y, self.w, self.h, Button.DEFAULT_OUTLINE_COLOR, False)
        self.touching_timeout += 1
        textlen = float(len(self.name))
        if textlen > 0.0:
            tx = self.x + self.w / 2.0 - (1.0/Button.DEFAULT_TEXT_RATIO * textlen / 2.0)
            ty = self.y + self.h / 2.0
            buff.text(self.name, tx, ty, Button.DEFAULT_TEXT_COLOR)

