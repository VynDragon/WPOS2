from enum import Enum

class KeyFunctions(Enum):
    SHIFT = 1
    BACKSPACE = 2
    MODE = 3
keyboard_mapping = []
keyboard_mapping[0] = ["q","w","e","r","t","y","u","i","o","p",
                    "a","s","d","f","g","h","j","k","l","'",
                    KeyFunctions.SHIFT,"z","x","c","v","b","n","m",KeyFunctions.BACKSPACE,KeyFunctions.BACKSPACE,
                    KeyFunctions.MODE, ",",""," "," "," "," ",".","\n","\n"]
keyboard_mapping[1] = ["Q","W","E","R","T","Y","U","I","O","P",
                    "A","S","D","F","G","H","J","K","L","\"",
                    KeyFunctions.SHIFT,"Z","X","C","V","B","N","M",KeyFunctions.BACKSPACE,KeyFunctions.BACKSPACE,
                    KeyFunctions.MODE, ":",""," "," "," "," ",";","\n","\n"]
keyboard_mapping[2] = ["1","2","3","4","5","6","7","8","9","0",
                    "@","#","$","_","&","-","+","(",")","/",
                    KeyFunctions.SHIFT,"*","\"","'",":",";","!","?",KeyFunctions.BACKSPACE,KeyFunctions.BACKSPACE,
                    KeyFunctions.MODE, ",",""," "," "," "," ",".","\n","\n"]

class Keyboard:
    def __init__():
        pass
