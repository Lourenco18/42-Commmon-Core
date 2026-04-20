def sculptor(string) -> str:
    s = ""
    p = True
    i = 0
    while i < len(string):
        if string[i].isalpha():
            if p:
                s += string[i].lower()
            else:
                s += string[i].upper()
            p = not p
        else:
            s += string[i]
        i+=1
    return s

print(sculptor("Hello world"))