# DONE
def cryptic_sorter(tlist):
    def vogais(s):
        return sum(c in "aeiou" for c in s.lower())
    final_list = sorted(tlist, key=lambda s: (len(s), s.lower(), s.isupper(), vogais(s)))
    return final_list

def reverseMatrix(s) -> list:
    return [e[::-1] for e in s]

def Pattern_tracker(s) -> int:
    thislist = []
    counter = 0
    i = 1
    while i < len(s):
        if s[i].isdigit() and s[i - 1].isdigit():
            if int(s[i]) == int(s[i-1]) + 1:
                counter +=1
        i+=1
    return counter

def twister(nums, n) -> list:
    if len(nums) == 0:
        return []
    n = n % len(nums)
    return nums[-n:] + nums[:-n]

def Anagram(s1, s2):
        if len(s1) != len(s2):
            return False
        return sorted(s1) == sorted(s2)



# NOT DONE
def isValid(s) -> bool:
    start = ['[', '{', '(']
    end = [']', '}', ')']
    temp = []
    i = 0
    while i < len(s):
        if s[i] in start:
            temp.append(s[i])
        elif(s[i] in end):
            if not temp:
                return false
            t = temp.pop()
            if s1[i] == ")" and t !="(":
                return false
            if s1[i] == "}" and t !="{":
                return false
            if s1[i] == "]" and t !="[":
                return false
        i+=1
        return len(temp) == 0

def Anagram(s1, s2):
        if len(s1) != len(s2):
            return False
        return sorted(s1) == sorted(s2)

def isPalindrome(s) -> bool:
    p = ""
    i = 0
    while i < len(s):
        if s[i].lower() >='a' and s[i].lower() <= 'z' :
            p += s[i].lower()
        i+=1
    return p == p[::-1]
    
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

def mergeList(list1, list2):
    if list1 is None:
        return sorted(list2)
    if list2 is None:
        return sorted(list1)

    final_list = []
    i = 0
    while i < len(list1):
        final_list.append(list1[i])
        i +=1
    i = 0
    while i < len(list2):
        final_list.append(list2[i])
        i +=1
    return sorted(final_list)

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

def convert_base(num: str, from_base: int, to_base: int) -> str:
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    try:
        if not 2 <= from_base <= 36:
            return "ERROR"
        if not 2 <= to_base <= 36:
            return "ERROR"
        
        n = int(num, from_base)
        if n == 0:
            return "0"
        
        res = ""
        while n:
            res += digits[n % to_base]
            n //= to_base
        
        return res[::-1]
    except Exception:
        return "ERROR"