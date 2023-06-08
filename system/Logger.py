from collections import deque

outputs = []
queue = deque((), 25)

def addOutput(func):
    outputs.append(func)

def removeOutput():
    outputs = outputs[:-1]

def log(text):
    queue.append(text)

def process(): # called from thread 0
    try:
        while len(queue) > 0:
            for out in outputs:
                out(queue.popleft())
    except IndexError as e:
            print(e)
