def sculptor(s)-> str:
    v = False
    p = ""
    for i in s:
        if i.isalpha():
            if v:
                p += i.upper()
            else:
                p += i.lower()
            v = not v
        else:
            p += i
    return p
# Basic case
print(sculptor("Hello world"))
# "hElLo WoRlD"