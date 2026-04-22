def mergeList(list1, list2):
    if list1 is None:
        return sorted(list2)
    if list2 is None:
        return sorted(list1)

    final_list = []
    i = 0
    while i < len(list1):
        final_list.append(list1[i])
        i +=1
    i = 0
    while i < len(list2):
        final_list.append(list2[i])
        i +=1
    return sorted(final_list)


print(mergeList(None, [0, 8, 2, 1]))
print(mergeList([99, -22, 10, 9], [2,4,5,9,8,3,4]))