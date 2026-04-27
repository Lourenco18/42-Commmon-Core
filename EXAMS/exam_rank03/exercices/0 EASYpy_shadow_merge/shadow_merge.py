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

print(mergeList(None, [0, 8, 2, 1]))
print(mergeList([99, -22, 10, 9], [2,4,5,9,8,3,4]))