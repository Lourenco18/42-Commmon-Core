def cryptic_sorter(tlist):
    def vogais(s):
        return sum(c in "aeiou" for c in s.lower())
    result = sorted(tlist, key=lambda s:(len(s),s.lower(), s.isupper(), vogais(s)))
    return result

def matrix(s):
    return [e[::-1] for e in s]

def Pattern_tracker(s):
    i =1
    counter = 0
    while i < len(s):
        if s[i].isdigit() and s[i-1].isdigit():
            if int(s[i]) == int(s[i-1]) +1:
                counter +=1
        i+=1
    return counter

def twister(nums,n):
    if len(nums)== 0:
        return []
    n = n%len(nums)
    return nums[-n:] + nums[:-n]

def anagram(s1,s2):
    if len(s2) != len(s1):
        return False
    return sorted(s1) == sorted(s2)

def isvalid(s):
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

def isPalindrome(s):
    p = ""
    for i in s:
        if i.isalpha():
            p +=i.lower()
    return p == p[::-1]

def sculptor(s):
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

def merge(l1,l2):
    if l1 is None:
        return sorted(l2)
    if l2 is None:
        return sorted(l1)
    final = []
    for i in l1:
        final += i
    for j in l2:
        final += j
    return sorted(final)

def Shift_alphabet(s,n):
    result = ""
    for i in s:
        if i.isalpha():
            if i.isupper():
                result += chr((ord(i) - ord('A')+ n)% 26 + ord('A'))
            else:
                result += chr((ord(i) - ord('a')+ n)% 26 + ord('a'))
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
            n //= to_base
        return result[::-1]
    except Exception:
        return "error"

        
