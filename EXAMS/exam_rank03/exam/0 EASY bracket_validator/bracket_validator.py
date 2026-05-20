def isValid(s)->bool:
    start = ['(','{','[']
    end =[')','}',']']
    temp = []
    for i in s:
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


print(isValid("{[()]}"))          # True
print(isValid("[{))}]"))          # False
print(isValid("hello(ppp)[pappap]{kkkk}"))  # true