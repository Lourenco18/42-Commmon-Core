
def isValid(s: str) -> bool:
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


print(isValid("{[()]}"))
print(isValid("[{))}]"))
print(isValid("hello(ppp)[pappap]{kkkk}"))
