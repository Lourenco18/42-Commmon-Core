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


print(isValid("{[()]}"))          # True
print(isValid("[{))}]"))          # False
print(isValid("hello(ppp)[pappap]{kkkk}"))  # true