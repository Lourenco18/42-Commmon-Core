from typing import List

def Pattern_tracker(string: str) -> int:
    thislist = []
    counter = 0
    for i in range(1, len(string)):
        if string[i].isdigit() and string[i - 1].isdigit():
            if int(string[i]) == int(string[i - 1])  + 1:
                counter += 1
    return counter


### Test ###
print(Pattern_tracker("123a345"))
print(Pattern_tracker("1a2b3c4d5"))
print(Pattern_tracker("12asd34hkh45kjhj56jhj67kjhjh78kjhjh89kjhkhj110"))
print(Pattern_tracker("111111"))
print(Pattern_tracker("012345"))