def isPalindrome(s) -> bool:
    temp = ""
    i = 0
    while i < len(s):
        if s[i].isalpha():
            temp += s[i].lower()
        i+=1
    return temp == temp[::-1]

print(isPalindrome("race a.,.2 car"))
print(isPalindrome("A man nama"))
print(isPalindrome("Able was I ere I saw Elba"))
print(isPalindrome("A man, a plan, a canal: Panama"))
