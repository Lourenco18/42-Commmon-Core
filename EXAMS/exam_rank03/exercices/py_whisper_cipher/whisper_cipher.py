
def Shift_alphabet(s: str, n: int):
    shift = ""
    for i in s:
        if 'a' <= i <= 'z':
            shift += chr((ord(i) - ord('a') + n) % 26 + ord('a'))
        elif 'A' <= i <= 'Z': 
            shift += chr((ord(i) - ord('A') + n) % 26 + ord('A'))
        else:
            shift += i
    return shift


print(Shift_alphabet("abz", 1))
print(Shift_alphabet("AbZ", 4))
print("Hello WOrld", 4)
print(ord('s'))
print(chr(65)) 