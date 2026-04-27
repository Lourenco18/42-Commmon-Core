def sculptor(s)-> str:
    p = ""
    i = 0
    v = False
    while i < len(s):
        if s[i].isalpha():
            if v:
                p += s[i].upper()
            else:
                p += s[i].lower()
            v = not v
        else:
            p += s[i]
        i+=1
    return p

# Basic case
print(sculptor("Hello world"))
# "hElLo WoRlD"