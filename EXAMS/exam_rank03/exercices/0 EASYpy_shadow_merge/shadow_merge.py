def mergeList(l1,l2)-> list:
    if l1 is None:
        return sorted(l2)
    if l2 is None:
        return sorted(l1)
    final = []
    for i in l1:
        final.append(i)
    for j in l2:
        final.append(j)

    return sorted(final)

print(mergeList(None, [0, 8, 2, 1]))
print(mergeList([99, -22, 10, 9], [2,4,5,9,8,3,4]))