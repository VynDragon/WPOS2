import PTRS
from system.Program import Program
import Single
import oframebuf
import framebuf
import time
import gc
import machine
import zlib


class bad_apple(Program):
    AUDIO_RATE = 4000.0
    #VIDEO_WIDTH = 200
    #VIDEO_HEIGHT = 200
    #FRAME_SIZE = int(200*200/8)
    #TARGET_FRAMETIME = 50
    VIDEO_WIDTH = 120
    VIDEO_HEIGHT = 120
    FRAME_SIZE = int(120*120/8)
    TARGET_FRAMETIME = 50

    def __init__(self, id = None, draw = False, arg = None):
        super().__init__(id, True)
        self.started = False
        self.video = None
        self.audio = None
        self.frame = None
        self.previousframe = None
        self.palette = None
        self.lastframe = 0
        self.data_ready = False
        self.update_timer = None

    def button_pressed(self):
        machine.freq(240000000) # I'm giving it all she's got captain!
        print(machine.freq())
        self.started = True
        self.lastframe = time.ticks_ms()


    def start(self):
        self.button = PTRS.Button(0.25,0.25,0.5,0.5, self.button_pressed,"Go")
        gc.collect() # yep
        self.lastframe = time.ticks_ms()
        self.palette = oframebuf.WPPalette()
        #if not Single.Hardware.readyAudio() and __debug__:
        #    print("Couldnt start audio")
        self.video = zlib.DecompIO(open("/largefiles/bad_apple_120_120.bw.gz", "rb"), 31)
        #self.video = open("/largefiles/bad_apple.bw", "rb")
        #self.audio = open("/largefiles/bad_apple.pcm_s16", "rb")
        #self.update_timer = machine.Timer(1, mode=machine.Timer.PERIODIC, freq=10, callback=self.update_frame)


    def stop(self):
        #self.update_timer.deinit()
        #Single.Hardware.releaseAudio()
        machine.freq(80000000)

    #@micropython.native
    def resize_fill_buffer_video(self):
        mulu = 2
        video_width = int(self.VIDEO_WIDTH / 8)
        video_height = int(self.VIDEO_HEIGHT / 8)
        frame_size = int(self.FRAME_SIZE)
        in_buff = bytearray(self.video.read(frame_size))
        out_buff = bytearray(video_width * 2 * video_height * 2)
        for h in range(0, video_height):
            for w in range(0, video_width):
                out_buff[h * mulu * video_width * mulu  + w * mulu] = \
                in_buff[h * video_width + w] & 0b10000000 + in_buff[h * video_width + w] & 0b10000000 >> 1 |\
                in_buff[h * video_width + w] & 0b01000000 >> 1 | in_buff[h * video_width + w] & 0b01000000 >> 2 |\
                in_buff[h * video_width + w] & 0b00100000 >> 2 | in_buff[h * video_width + w] & 0b00100000 >> 3 |\
                in_buff[h * video_width + w] & 0b00010000 >> 3 | in_buff[h * video_width + w] & 0b00010000 >> 4
                out_buff[h * mulu * video_width * mulu   + w * mulu + 1] = \
                in_buff[h * video_width + w] & 0b00001000 << 4 | in_buff[h * video_width + w] & 0b00001000 << 3 |\
                in_buff[h * video_width + w] & 0b00000100 << 3 | in_buff[h * video_width + w] & 0b00000100 << 2 |\
                in_buff[h * video_width + w] & 0b00000010 << 2 | in_buff[h * video_width + w] & 0b00000010 << 1 |\
                in_buff[h * video_width + w] & 0b00000001 << 1 | in_buff[h * video_width + w] & 0b00000001
                out_buff[h * mulu * video_width * mulu  + w * mulu + video_width * mulu] = out_buff[h * mulu * video_width * mulu  + w * mulu]
                out_buff[h * mulu * video_width * mulu  + w * mulu + 1 + video_width * mulu] = out_buff[h * mulu * video_width * mulu  + w * mulu + 1]


        return out_buff

    def update_frame(self):
        try:
            self.previousframe = self.frame
            self.frame = bytearray(self.video.read(self.FRAME_SIZE))
            while(time.ticks_ms() - self.lastframe < self.TARGET_FRAMETIME): # attempt to hold 20 fps
                time.sleep(0)
            frametime = time.ticks_ms() - self.lastframe
            if __debug__:
                print("movie frame preparation time:", frametime)

            if frametime > self.TARGET_FRAMETIME: # time compensation i guess?
                self.lastframe = time.ticks_ms() - (frametime - self.TARGET_FRAMETIME)
            else:
                self.lastframe = time.ticks_ms()
            self.data_ready = True

            #eightbit = bytearray(self.audio.read(int(100.0/1000.0/self.AUDIO_RATE)))
            #Single.Hardware.writeAudio(eightbit)
        except:
            pass

    def think(self):
        if self.started:
            self.update_frame()
        else:
            try:
                while True: #event treatment
                    event = self.input.popleft()
                    self.button.event(event)
            except IndexError:
                pass
            time.sleep(0)

    @micropython.native
    def draw(self, buff):
        if not self.started:
            self.button.draw(buff)
        else:
            if self.previousframe != None:
                tmpbuf = oframebuf.FrameBuffer(self.previousframe, self.VIDEO_WIDTH, self.VIDEO_HEIGHT, framebuf.MONO_HLSB)
                buff.blit(tmpbuf, 0.25, 0.25, -1, self.palette)
                self.data_ready = False
