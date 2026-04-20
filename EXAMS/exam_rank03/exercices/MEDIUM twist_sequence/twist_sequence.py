def rotate_rigth(nums,n) -> list:
    rotated = []
    i = len(nums) - n
    while i < len(nums):
        rotated.append(nums[i])
        i +=1
    i = 0
    while i < (len(nums) - n):
        rotated.append(nums[i])
        i +=1
    return rotated

def rotate_left(nums,n) -> list:
    rotated = []
    lista = []
    n = -n
    i = 0
    while i < n:
        lista.append(nums[i])
        i +=1
    i = n
    while i < len(nums) :
        rotated.append(nums[i])
        i +=1
    i = 0
    while i < len(lista):
        rotated.append(lista[i])
        i +=1
    return rotated
            
            
def twister(nums,n)-> list:
    result = []
    if len(nums)>1:
        if n <0:
            if n > len(nums):
                n = (len(nums)) -1
            result = rotate_left(nums,n)
        elif n > 0:
            if n > len(nums):
                n = (len(nums)) -1
            result = rotate_rigth(nums,n)

        else:
            result = nums
    else:
        result = nums
    return result


print(twister([1, 2, 3, 4, 5], 2))
print(twister([4, 2, 1, -1, 'a'], 4))
print(twister([1, 2, 3], 3))
print(twister([1, 2, 3], 5))
print(twister([1], 10))
print(twister([] , 3))
print(twister([1, 2, 3, 4], -1))

