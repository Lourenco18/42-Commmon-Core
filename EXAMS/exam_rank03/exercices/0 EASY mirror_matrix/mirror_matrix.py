
def reverseMatrix(s) -> list:
    return [e[::-1] for e in s]
    
inpu = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
print(reverseMatrix(inpu))