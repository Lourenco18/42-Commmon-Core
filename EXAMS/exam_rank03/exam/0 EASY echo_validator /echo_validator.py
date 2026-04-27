def isPalindrome(s) -> bool:
    p = ""
    for i in s:
        if i.isalpha():
            p +=i.lower()
    return p == p[::-1]

print(isPalindrome("race e.,.2 car"))
print(isPalindrome("A man nama"))
print(isPalindrome("Able was I ere I saw Elba"))
print(isPalindrome("A man, a plan, a canal: Panama"))
