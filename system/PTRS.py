# word play on buttoning, buttons. and the PTRS anti-tank rifle
# graphics for pretty buttons

import Events
import Single
import framebuf, oframebuf


class Generic: # monkeypatch draw function on this when instanciating
    def __init__(self, name = ""):
        self.name = name

    def event(self, event):
        pass

    def draw(self, buff):
        pass

class Button(Generic):
    TOUCH_LAST = 5 # 5 frames

    def __init__(self, x, y, w, h, callback = None, name = ""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.name = name
        self.touching = False
        self.touching_timeout = 5
        self.callback = callback
        if callback == None:
            self.callback = self.default_callback

    def default_callback(self):
        Single.Kernel.event(Events.ButtonEvent(self))

    @micropython.native
    def event(self, event):
        if isinstance(event, Events.ReleaseEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.callback()
                self.touching_timeout = 0
        if isinstance(event, Events.TouchEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.touching_timeout = 0

    @micropython.native
    def draw(self, buff):
        if self.touching_timeout < Button.TOUCH_LAST:
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR, True)
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_COLOR, False)
        else:
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_COLOR, True)
            buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR, False)
        self.touching_timeout += 1
        textlen = float(len(self.name))
        if textlen > 0.0:
            tx = self.x + self.w / 2.0 - Single.DEFAULT_TEXT_RATIO_INV_2 * textlen
            ty = self.y + self.h / 2.0 - Single.DEFAULT_TEXT_RATIO_INV_2
            buff.text(self.name, tx, ty, Single.DEFAULT_TEXT_COLOR)

class Slider(Generic):

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


class Switch(Generic):
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

class TextField(Generic):
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

class Graph(Generic):
    def __init__(self, x, y, w, h, bg = True, callback = None, name = ""):
        self.x = x
        self.y = y
        self.w = w
        self.rw = int(w * Single.Hardware.DISPLAY_WIDTH)
        self.h = h
        self.rh = int(h * Single.Hardware.DISPLAY_HEIGHT)
        self.bg = bg
        self.name = name
        self.callback = callback
        self.last_value = 0.0
        if callback == None:
            self.callback = self.default_callback
        self.draw_buff = oframebuf.FrameBuffer(bytearray(self.rw * self.rh * 2), self.rw, self.rh, framebuf.RGB565)
        if self.bg:
            self.draw_buff.rect(0, 0, self.rw, self.rh, Single.DEFAULT_COLOR, True)
    def default_callback(self):
        pass

    @micropython.native
    def event(self, event):
        if isinstance(event, Events.ReleaseEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.callback()

    @micropython.native
    def draw(self, buff):
        buff.blit(self.draw_buff, self.x, self.y)
        buff.rect(self.x, self.y, self.w, self.h, Single.DEFAULT_OUTLINE_COLOR)

    @micropython.native
    def add_point(self, value, color = Single.DEFAULT_TEXT_COLOR):
        self.draw_buff.scroll(-1, 0)
        self.draw_buff.vline(self.rw - 2, 0, self.rh, Single.DEFAULT_COLOR)
        self.draw_buff.line(self.rw - 2, int((1.0 - self.last_value) * self.rh), self.rw - 2, int((1.0 - value) * self.rh), color)
        self.last_value = value


class Scrollable(Generic):
    def __init__(self, x, y, w, h, w_mul = 1, h_mul = 2, name = ""):
        self.x = x
        self.y = y
        self.w = w
        self.w_mul = w_mul
        self.h_mul = h_mul
        self.rw = int(w * Single.Hardware.DISPLAY_WIDTH)
        self.h = h
        self.rh = int(h * Single.Hardware.DISPLAY_HEIGHT)
        self.name = name
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.last_touch = (0,0)
        self.elements = []

    @micropython.native
    def event(self, event):
        if isinstance(event, Events.ReleaseEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                diffx = event.x - self.last_touch[0]
                diffy = event.y - self.last_touch[1]
                self.offset_x -= diffx
                self.offset_y -= diffy
                if self.offset_x > 0:
                    self.offset_x = 0
                elif self.offset_x < - self.w * (self.w_mul - 1):
                    self.offset_x = - self.w * (self.w_mul - 1)
                if self.offset_y > 0:
                    self.offset_y = 0
                elif self.offset_y <  - self.h * (self.h_mul - 1):
                    self.offset_y = - self.h * (self.h_mul - 1)
                else:
                    for element in self.elements:
                        element.event(event)
        if isinstance(event, Events.TouchEvent):
            if event.x > self.x and event.x < self.x + self.w and event.y > self.y and event.y < self.y + self.h:
                self.last_touch = (event.x, event.y)

    @micropython.native
    def draw(self, buff):
        for elem in self.elements:
            elem.draw(self.draw_buff)
        buff.blit(self.draw_buff, self.x + self.offset_x, self.y + self.offset_y)

    def add_element(self, element: Generic):
        self.elements.append(element)






