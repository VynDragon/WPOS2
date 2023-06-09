class Event:
    def __init__(self, t = None, s = None):
        self.t_program_id = t
        self.s_program_id = s

class FrontEvent(Event):
    def __init__(self, t = None, s = None):
        self.t_program_id = t
        self.s_program_id = s

class RunEvent(Event):
    def __init__(self, programname, arg = None, t = None, s = None):
        self.name = programname
        self.arg = arg
        super().__init__(t, s)

class StopEvent(Event):
    def __init__(self, programname, t = None, s = None):
        self.name = programname
        super().__init__(t, s)

class TouchEvent(FrontEvent):
    def __init__(self, x, y, t = None, s = None):
        self.x = x
        self.y = y
        self.t_program_id = t
        self.s_program_id = s # it doesnt like if spam, recursion error because of super() when called from irq handler, so go... manual unfolding?

class ReleaseEvent(FrontEvent):
    def __init__(self, x, y, t = None, s = None):
        self.x = x
        self.y = y
        super().__init__(t, s)

class GestureEvent(Event):
    def __init__(self, gesture, t = None, s = None):
        self.gesture = gesture
        super().__init__(t, s)

class ButtonEvent(Event):
    def __init__(self, button, t = None, s = None):
        self.button = button
        super().__init__(t, s)

class PhysButtonEvent(Event):
    def __init__(self, time, t = None, s = None):
        self.time = time
        super().__init__(t, s)


class SliderEvent(Event):
    def __init__(self, slider, t = None, s = None):
        self.slider = slider
        super().__init__(t, s)

class TextInputEvent(FrontEvent):
    def __init__(self, text, t = None, s = None):
        self.text = text
        super().__init__(t, s)

class TextFieldEvent(Event): #Textfield update
    def __init__(self, field, t = None, s = None):
        self.field = field
        super().__init__(t, s)

class IMUEvent(Event):
    def __init__(self, int, t = None, s = None):
        self.int = int
        super().__init__(t, s)

