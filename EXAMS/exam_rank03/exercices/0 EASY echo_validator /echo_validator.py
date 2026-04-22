
def isPalindrome(s) -> bool:
    p = ""
    i = 0
    while i < len(s):
        if s[i].lower() >='a' and s[i].lower() <= 'z' :
            p += s[i].lower()
        i+=1
    return p == p[::-1]

print(isPalindrome("race a car"))
print(isPalindrome("A man nama"))
print(isPalindrome("Able was I ere I saw Elba"))
print(isPalindrome("A man, a plan, a canal: Panama"))
