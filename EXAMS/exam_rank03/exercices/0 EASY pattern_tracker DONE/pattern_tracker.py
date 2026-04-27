def Pattern_tracker(s) -> int:
    result = []
    counter = 0
    i = 1 
    while i < len(s):
        if s[i].isdigit() and s[i-1].isdigit():
            if int(s[i]) == int(s[i-1]) +1:
                counter +=1
        i += 1
    return counter



print(Pattern_tracker("123a345"))
print(Pattern_tracker("1a2b3c4d5"))
print(Pattern_tracker("12asd34hkh45kjhj56jhj67kjhjh78kjhjh89kjhkhj110"))
print(Pattern_tracker("111111"))
print(Pattern_tracker("98"))