from system.Program import Program
import Single
import framebuf, time
import Events

class KeyFunctions: # no enum lol
    SHIFT = "/\\"
    BACKSPACE = "<-"
    MODE = "?!"


keyboard_mapping = [
                    ["q","w","e","r","t","y","u","i","o","p",
                    "a","s","d","f","g","h","j","k","l","'",
                    KeyFunctions.SHIFT,"z","x","c","v","b","n","m",KeyFunctions.BACKSPACE,KeyFunctions.BACKSPACE,
                    KeyFunctions.MODE, KeyFunctions.MODE,","," "," "," "," ",".","\n","\n"],
                    ["Q","W","E","R","T","Y","U","I","O","P",
                    "A","S","D","F","G","H","J","K","L","\"",
                    KeyFunctions.SHIFT,"Z","X","C","V","B","N","M",KeyFunctions.BACKSPACE,KeyFunctions.BACKSPACE,
                    KeyFunctions.MODE, KeyFunctions.MODE,":"," "," "," "," ",";","\n","\n"],
                    ["1","2","3","4","5","6","7","8","9","0",
                    "@","#","$","_","&","-","+","(",")","/",
                    KeyFunctions.SHIFT,"*","\"","'",":",";","!","?",KeyFunctions.BACKSPACE,KeyFunctions.BACKSPACE,
                    KeyFunctions.MODE, KeyFunctions.MODE,","," "," "," "," ",".","\n","\n"]
                    ]

class keyboard(Program):
    KB_HEIGHT = 0.8
    KB_WIDTH = 1.0

    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.mode = 0
        self.text = ""
        if arg != None:
            self.text = arg
        self.backing = [None, None, None]

        self.startx = 0.0
        self.endx = self.startx + self.KB_WIDTH
        self.starty = 1.0 - self.KB_HEIGHT
        self.endy = 1.0
        self.lx = self.endx - self.startx
        self.ly = self.endy - self.starty
        self.sx = self.lx / 10.0
        self.sy = self.ly / 4.0

    def think(self):
        try:
            while True: #event treatment
                event = self.input.popleft()
        except IndexError:
            pass
        time.sleep_ms(1000)

    @micropython.native
    def key(self, x, y):
        if x >= self.startx and y >= self.starty and y <= self.endy and x <= self.endx:
            return keyboard_mapping[self.mode][int(x/self.sx) + 10*int((y - self.starty)/self.sy)]
        else:
            return None

    def event(self, event):
        if isinstance(event, Events.ReleaseEvent):
            k = self.key(event.x, event.y)
            if k == KeyFunctions.SHIFT and self.mode == 0:
                self.mode = 1
            elif k == KeyFunctions.SHIFT and self.mode == 1:
                self.mode = 0
            elif k == KeyFunctions.MODE and self.mode < 2:
                self.mode = 2
            elif k == KeyFunctions.MODE and self.mode == 2:
                self.mode = 0
            elif k == KeyFunctions.BACKSPACE:
                self.text = self.text[:-1]
            elif k == None:
                Single.Kernel.event(Events.StopEvent(self.thread))
            elif k != KeyFunctions.BACKSPACE and k != KeyFunctions.MODE and k != KeyFunctions.SHIFT:
                self.text = self.text + k
        else:
            super().event(event)

    def stop(self):
        Single.Kernel.event(Events.TextInputEvent(self.text))



    @micropython.native
    def drawKb(self, buff):
        buff.rect(self.startx, self.starty, self.KB_WIDTH, self.KB_HEIGHT, Single.DEFAULT_COLOR, True)
        buff.rect(self.startx, self.starty, self.KB_WIDTH, self.KB_HEIGHT, Single.DEFAULT_OUTLINE_COLOR, False)
        for ky in range(0,4):
            if ky > 0:
                buff.hline(0,self.starty+ky*self.sy,1.0,Single.DEFAULT_OUTLINE_COLOR)
            for kx in range(0,10):
                buff.text(keyboard_mapping[self.mode][kx + 10 * ky], self.startx + self.sx * kx + 0.02, self.starty + self.sy * ky + 0.02,Single.DEFAULT_TEXT_COLOR)

    @micropython.native
    def draw(self, buff):
        buff.fill(0)
        self.drawKb(buff)
        buff.rect(0, 0.03, 1.0, 0.13, Single.DEFAULT_OUTLINE_COLOR, False)
        buff.text(self.text, 0, 0.07, Single.DEFAULT_TEXT_COLOR)
