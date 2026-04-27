def Shift_alphabet(s,n):
    result = ""
    for i in s:
        if i.isalpha():
            if i.isupper():
                result += chr((ord(i) - ord('A') + n) % 26 + ord('A'))
            else:
                result += chr((ord(i) - ord('a') + n) % 26 + ord('a'))
        else:
            result += i
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