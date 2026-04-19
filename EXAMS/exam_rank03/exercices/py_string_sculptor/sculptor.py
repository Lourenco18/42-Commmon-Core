
def sculptor(text: str) -> str:
    s = ""
    i = 0
    p = True
    while i < len(text):
        if text[i].isalpha():
            if p:
                s += text[i].lower()
            else:
                s += text[i].upper()
            p = not p
        else:
            s += text[i]
        i += 1
    return s


### Test ###
print(sculptor("Hello world"))

