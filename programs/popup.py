from system.Program import Program
import Single
import PTRS
import time
import Events

class popup(Program):
    def __init__(self, id = None, draw = False, arg = ""):
        super().__init__(id, True)
        self.ok = None
        self.text = arg

    def think(self):
        try:
            while True:
                event = self.input.popleft()
                self.ok.event(event)
        except IndexError:
            pass
        time.sleep(0)

    def draw(self, buff):
        buff.fill(0)
        buff.rect(0.1, 0.25, 0.8, 0.5, Single.DEFAULT_BG_COLOR, True)
        buff.rect(0.1, 0.25, 0.8, 0.5, Single.DEFAULT_OUTLINE_COLOR, False)
        textlen = float(len(self.text))
        if textlen > 0.0:
            tx =  0.5 - Single.DEFAULT_TEXT_RATIO_INV_2 * textlen
            ty = 0.3 - Single.DEFAULT_TEXT_RATIO_INV_2
            buff.text(self.text, tx, ty, Single.DEFAULT_TEXT_COLOR)
        self.ok.draw(buff)

    def start(self):
        self.ok = PTRS.Button(0.3, 0.6, 0.4, 0.1, callback = lambda: Single.Kernel.event(Events.StopEvent(self.thread)), name = "OK")

