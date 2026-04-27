def Shift_alphabet(s,n):
    result = ""
    i = 0
    while i < len(s):
        if s[i].isalpha():
            if s[i].islower():
                result+=chr((ord(s[i])- ord('a') + n)% 26 + ord('a'))
            else:
                result+=chr((ord(s[i])- ord('A') + n)% 26 + ord('A'))
        else:  
            result += s[i]
        i+=1
    return result 
# Basic cases
print(Shift_alphabet("abz", 1))
# "bca"

print(Shift_alphabet("AbZ", 1))
# "BcA"

# With spaces and punctuation
print(Shift_alphabet("Hello World!", 3))
# "Khoor Zruog!"

# Negative shift
print(Shift_alphabet("bca", -1))
# "abz"

# Large shift (wrap around)
print(Shift_alphabet("abc", 26))
# "abc"

print(Shift_alphabet("xyz", 3))
# "abc"

# Mixed characters
print(Shift_alphabet("Python 3.8!", 5))
# "Udymts 3.8!"

# Edge cases
print(Shift_alphabet("", 10))
# ""

print(Shift_alphabet("12345", 4))
# "12345"