# DONE
def cryptic_sorter(tlist):
    def vogais(s):
        return sum(c in "aeiou" for c in s.lower())
    result = sorted(tlist, key=lambda s:(len(s),s.lower(),s.isupper(), vogais(s)))
    return result

def reverseMatrix(s) -> list:
    return [e[::-1] for e in s]

def Pattern_tracker(s) -> int:
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
       start = ['(','{','[']
    end =[')','}',']']
    temp = []
    for i in c:
        if i in start:
            temp.append(i)
        elif i in end:
            if not temp:
                return False
            t = temp.pop()
            if i == ')' and t !='(':
                return False
            if i == '}' and t !='{':
                return False
            if i == ']' and t !='[':
                return False
    return len(temp) == 0

def isPalindrome(s) -> bool:
    p = ""
    for i in s:
        if i.isalpha():
            p +=i.lower()
    return p == p[::-1]

def sculptor(string) -> str:
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

def mergeList(ls1,ls2)-> list:
    new_list = []
    if  ls1 is None:
        return sorted(ls2)
    if ls2 is None:
        return sorted(ls1)
    i = 0
    while i < len(ls1):
        new_list.append(ls1[i])
        i+=1
    i = 0
    while i < len(ls2):
        new_list.append(ls2[i])
        i+=1
    return sorted(new_list)

def Shift_alphabet(s,n) -> str:
    result = ""
    for i in s:
        if i.isalpha():
            if i.isupper():
                result += chr((ord(i) - ord('A') +n) % 26 + ord('A'))
            else:
                result += chr((ord(i) - ord('a') +n) %26 + ord('a'))
        else:
            result +=i
    return result

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



#treino PERFEITO
def cryptic_sorter(tlist):
    def vogais(s):
        return sum(c in "aeiou" for c in s.lower())
    result = sorted(tlist, key=lambda s:(len(s),s.lower(),s.isupper(), vogais(s)))
    return result

def reverseMatrix(s):
    return [e[::-1] for e in s]

def Pattern_tracker(s):
    i = 1
    counter = 0
    while i < len(s):
        if s[i].isdigit() and s[i-1].isdigit():
            if int(s[i]) == int(s[i-1]) +1:
                counter +=1
        i +=1
    return counter

def twister(nums,n):
    if len(nums) == 0:
        return []
    n = n % len(nums)
    return nums[-n:] + nums[:-n]

def Anagram(s1,s2):
    if len(s1) != len(s2):
        return False
    return sorted(s1) == sorted(s2)

#treino novidades 
def isValid(s)->bool:
    start = ['(', '{', '[']
    end = [')', '}', ']']
    i = 0
    temp = []
    while i < len(s):
        if s[i] in start:
            temp.append(s[i])
        elif s[i] in end:
            if not temp:
                return False
            t = temp.pop()
            if s[i] == ')' and t!='(':
                return False
            if s[i] == '}' and t!='{':
                return False
            if s[i] == ']' and t!='[':
                return False
        i +=1
    return len(temp) == 0

def isPalindrome(s) -> bool:
    temp = ""
    i = 0
    while i < len(s):
        if s[i].isalpha():
            temp += s[i].lower()
        i+=1
    return temp == temp[::-1]

def sculptor(s)-> str:
    p = ""
    i = 0
    v = False
    while i < len(s):
        if s[i].isalpha():
            if v:
                p += s[i].upper()
            else:
                v = not v
                p += s[i].lower()
        else:
            p += s[i]
        i+=1
    return p

def mergeList(ls1,ls2)-> list:
    new_list = []
    if len(ls1) == 0:
        return ls2
    if len(ls2) == 0:
        return ls1
    i = 0
    while i < len(ls1):
        new_list.append(ls1[i])
        i+=1
    i = 0
    while i < len(ls2):
        new_list.append(ls2[i])
        i+=1
    return sorted(new_list)

def Shift_alphabet(s,n):
    result = ""
    for i in s:
        if i.isalpha():
            if i.isupper():
                shift += chr((ord(i) - ord('A') + n) % 26 + ord('A'))
            else:
                shift += chr((ord(i) - ord('a') + n) % 26 + ord('a'))
        else:
            result += i
    return result

def convert_base(num, from_base,to_base):
    digits = "0123456789ABCDEFGHIJKLMNOPRSTUVWXYZ"
    try:
        if not 2 <= from_base <= 36:
            return "error"
        if not 2 <= to_base <= 36:
            return "error"
        n = int(num,from_base)
        if n == 0:
            return "0"
        res = ""
        while n:
            res += digits[n % to_base]
            n //= to_base
        return res[::-1]
    except Exception:
        return "error"

def Shift_alphabet(s,n):
    result = ""
    for i in s:
        if i.isalpha():
            if i.isupper():
                result += chr((ord(i) - ord('A') + n)% 26 + ord('A')) 
            else:
                result += chr((ord(i) - ord('a') + n)% 26 + ord('a')) 
        else:
            result +=i
    return result

def convert_base(num, from_base,to_base):
    digits = "0123456789ABCDEFGHIJKLMNOPRSTUVWXYZ"
    try:
        if not 2 <= from_base <= 36:
            return "error"
        if not 2 <= to_base <= 36:
            return "error"
        n = int(num,from_base)
        if n == 0:
            return "0"
        result = ""
        while n:
            result += digits[n % to_base]
            n //=to_base
        return result[::-1]
    except Exception:
        return "error"
    