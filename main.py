import uasyncio as asyncio
from system.Kernel import Kernel

def set_global_exception():
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)


set_global_exception()  # Debug aid
my_class = Kernel()  # Constructor might create tasks
my_class.run_forever()  # Non-terminating method

''''async def main():
    set_global_exception()  # Debug aid
    my_class = Kernel()  # Constructor might create tasks
    await my_class.run_forever()  # Non-terminating method

Logger.addOutput(print)



try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()  # Clear retained state'''
