# word play on buttoning, buttons. and the PTRS anti-tank rifle
# graphics for pretty buttons

import Events
import Single

class Button:
    TOUCH_LAST = 5 # 5 frames

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
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR, True)
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_COLOR, False)
        else:
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_COLOR, True)
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR, False)
        self.touching_timeout += 1
        textlen = float(len(self.name))
        if textlen > 0.0:
            tx = self.x + self.w / 2.0 - (1.0/Single.DEFAULT_TEXT_RATIO * textlen / 2.0)
            ty = self.y + self.h / 2.0 - Single.DEFAULT_TEXT_RATIO_INV_2
            buff.text(self.name, tx, ty, Single.DEFAULT_TEXT_COLOR)

class Slider:

    def __init__(self, x, y, w, h, value = 0.5, callback = None, name = ""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.name = name
        self.touching = False
        self.touching_timeout = 0
        self.callback = callback
        self.value = value
        if callback == None:
            self.callback = self.default_callback

    def default_callback(self):
        Single.Kernel.event(Events.SliderEvent(self))

    @micropython.native
    def event(self, event):
        if isinstance(event, Events.ReleaseEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.value = (event.x - self.x) / self.w
                self.callback()
        if isinstance(event, Events.TouchEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.value = (event.x - self.x) / self.w
                self.callback()

    @micropython.native
    def draw(self, buff):
        buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_COLOR, True)
        buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR, False)
        buff.rect(self.x + self.value * self.w, self.y + 0.025, 0.02, self.h - 0.05, Single.DEFAULT_TEXT_COLOR, True)


class Switch:
    def __init__(self, x, y, w, h, value = False, callback = None, name = ""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.name = name
        self.touching_display = False
        self.value = value
        self.callback = callback
        if callback == None:
            self.callback = self.default_callback

    def default_callback(self):
        Single.Kernel.event(ButtonEvent(self))

    @micropython.native
    def event(self, event):
        if isinstance(event, Events.ReleaseEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.value = not self.value
                self.callback()
            self.touching_display = False
        if isinstance(event, Events.TouchEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.touching_display = True
            else:
                self.touching_display = False

    @micropython.native
    def draw(self, buff):
        if self.touching_display:
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR, True)
        else:
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_COLOR, True)
        if self.value:
            buff.rect(self.x+self.w/2.0, self.y + self.h/4.0, self.w/2.0, self.h/2.0, Single.DEFAULT_YESCOLOR, True)
        else:
            buff.rect(self.x+self.w/2.0, self.y + self.h/4.0, self.w/2.0, self.h/2.0, Single.DEFAULT_NOCOLOR, True)
        if self.touching_display:
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_COLOR, False)
        else:
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR, False)
        textlen = float(len(self.name))
        if textlen > 0.0:
            tx = self.x + 0.05
            ty = self.y + self.h / 2.0
            buff.text(self.name, tx, ty, Single.DEFAULT_TEXT_COLOR)

class TextField:
    def __init__(self, x, y, w, h, value = "", hide_contents = False, callback = None, name = ""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.name = name
        self.value = value
        self.callback = callback
        self.hide_contents = hide_contents
        if callback == None:
            self.callback = self.default_callback

    def default_callback(self):
        Single.Kernel.event(TextFieldEvent(self))

    @micropython.native
    def event(self, event):
        if isinstance(event, Events.ReleaseEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                Single.Kernel.event(Events.RunEvent("keyboard", self.value))
        elif isinstance(event, Events.TextInputEvent):
            self.value = event.text
            self.callback()

    @micropython.native
    def draw(self, buff):
        buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR, False)
        if self.hide_contents:
            fstr = "*" * len(self.value)
            buff.text(fstr, self.x, self.y + self.h / 2.0 - Single.DEFAULT_TEXT_RATIO_INV_2, Single.DEFAULT_TEXT_COLOR)
        else:
            buff.text(self.value, self.x, self.y + self.h / 2.0 - Single.DEFAULT_TEXT_RATIO_INV_2, Single.DEFAULT_TEXT_COLOR)


