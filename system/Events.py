class Event:
    def __init__(self, t = None, s = None):
        self.t_program_id = t
        self.s_program_id = s


class RunEvent(Event):
    def __init__(self, programname, t = None, s = None):
        self.name = programname
        super().__init__(t, s)

class StopEvent(Event):
    def __init__(self, programname, t = None, s = None):
        self.name = programname
        super().__init__(t, s)

class TouchEvent(Event):
    def __init__(self, x, y, t = None, s = None):
        self.x = x
        self.y = y
        super().__init__(t, s)

class ReleaseEvent(Event):
    def __init__(self, x, y, t = None, s = None):
        self.x = x
        self.y = y
        super().__init__(t, s)

class ButtonEvent(Event):
    def __init__(self, button, t = None, s = None):
        self.button = button
        super().__init__(t, s)


class SliderEvent(Event):
    def __init__(self, slider, t = None, s = None):
        self.slider = slider
        super().__init__(t, s)

class TextInputEvent(Event):
    def __init__(self, text, t = None, s = None):
        self.text = text
        super().__init__(t, s)

