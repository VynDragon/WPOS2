class Event:
    def __init__(self, t = None, s = None):
        self.t_program_id = t
        self.s_program_id = s


class RunEvent(Event):
    def __init__(self, programname, t = None, s = None):
        self.name = programname
        super().__init__(t, s)

class StopEvent(RunEvent):
    pass

class TouchEvent(Event):
    def __init__(self, x, y, t = None, s = None):
        self.x = x
        self.y = y
        super().__init__(t, s)

class ReleaseEvent(TouchEvent):
    pass

class ButtonEvent(Event):
    def __init__(self, button, t = None, s = None):
        self.button = button
        super().__init__(t, s)

