import PTRS
from system.Program import Program
import Events
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
        self.frame = bytearray(self.FRAME_SIZE)
        self.previousframe = None
        self.palette = None
        self.nextframetime = None
        self.data_ready = False
        self.update_timer = None

    def button_pressed(self):
        machine.freq(240000000) # I'm giving it all she's got captain!
        print(machine.freq())
        self.started = True
        self.nextframetime = time.ticks_us()

    def start(self):
        self.button = PTRS.Button(0.25,0.25,0.5,0.5, self.button_pressed,"Go")
        gc.collect() # yep
        self.palette = oframebuf.WPPalette()
        #if not Single.Hardware.readyAudio() and __debug__:
        #    print("Couldnt start audio")
        the_video_file = open("/largefiles/bad_apple_120_120.bw.gz", "rb")
        magic =0
        try:
            magic = the_video_file.read(2)
        except:
            pass
        if magic != bytes([0x1f, 0x8b]):
            return Single.Kernel.event(Events.StopEvent(self.thread))
        the_video_file.seek(0,0)
        self.video = zlib.DecompIO(the_video_file, 31)
        #self.video = open("/largefiles/bad_apple.bw", "rb")
        #self.audio = open("/largefiles/bad_apple.pcm_s16", "rb")
        #self.update_timer = machine.Timer(1, mode=machine.Timer.PERIODIC, freq=10, callback=self.update_frame)


    def stop(self):
        #self.update_timer.deinit()
        #Single.Hardware.releaseAudio()
        Single.Hardware.set_freq()

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
            tick_diff = time.ticks_diff(self.nextframetime, time.ticks_us())  # correct way, beeg precision
            if tick_diff <= 0:
                self.nextframetime = time.ticks_add(time.ticks_us(), tick_diff) # hopefully that's enough speed correction, otherwise we might need to calculate a exact offset using the rtc instead
                #print(self.nextframetime, time.ticks_us(), tick_diff)
                video_frame = self.video.readinto(self.frame) # bad habit of crashing the esp when reaching end of file without reporting it
                if video_frame != self.FRAME_SIZE: # end of file
                    self.started = False
                    self.previousframe = None
                    return

                self.data_ready = True
                self.nextframetime = time.ticks_add(self.nextframetime, self.TARGET_FRAMETIME * 1000)

            #eightbit = bytearray(self.audio.read(int(100.0/1000.0/self.AUDIO_RATE)))
            #Single.Hardware.writeAudio(eightbit)
        except:
            self.started = False # also end of file
            self.previousframe = None

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
