Kernel = None
Hardware = None
Settings = None
fucky_wucky = False



#DEFAULT_COLOR = 0xB5B6
DEFAULT_COLOR = 0x5155
DEFAULT_BG_COLOR = 0
DEFAULT_OUTLINE_COLOR = 0x7BCF
DEFAULT_TEXT_COLOR = 0xFFFF
DEFAULT_YESCOLOR = DEFAULT_OUTLINE_COLOR
DEFAULT_NOCOLOR = DEFAULT_BG_COLOR
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240
DEFAULT_TEXT_RATIO = DISPLAY_WIDTH / 8  #characters per line, 30 for 240x240 screen with 8 pixel large font
DEFAULT_TEXT_RATIO_INV = 1.0/DEFAULT_TEXT_RATIO  #expensive maths
DEFAULT_TEXT_RATIO_INV_2 = DEFAULT_TEXT_RATIO_INV/2.0
DEFAULT_TEXT_RATIO_HEIGHT = DISPLAY_HEIGHT / 8
DEFAULT_TEXT_RATIO_INV_HEIGHT = 1.0/DEFAULT_TEXT_RATIO_HEIGHT

MP_THREAD_STACK_SIZE = 8 * 1024 # bruh
MP_SMALLTHREAD_STACK_SIZE = 1024 # bruh

'''
it refuses to do more than 64*1024, but it's only 64 kb and we still hit bs recursion errors in non-recursive code...

Turns out it was really dumb:
https://github.com/orgs/micropython/discussions/10614
"The impression that _thread.stack_size() would not work came from the behavior that calling it without arguments reports the previously set value but at the same time sets the stack size silently back to 4K.
So print('New Stack Size=', _thread.stack_size()) prints nicely the previously set value but makes this setting invalid.
Taking that into account, the place where e.g. _thread.stack_size(8*1024) is called seems to be not critical anymore."

Comments say this is *intended*


Fixing that in my code immediatly caused wifi driver to run out of memory ('unknown error 0x0101') so it's working

Also I was testing on the V2, which has 4MB of ram instead of 8MB and made the error easy to hit'''
