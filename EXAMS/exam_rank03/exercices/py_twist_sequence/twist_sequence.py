from collections import deque
from typing import List
def twister(nums: List[int], n: int):
    thislist = []
    dq = deque(nums)
    dq.rotate(n)
    return list(dq)


## Test ### 
print(twister([1, 2, 3, 4, 5], 2))
print(twister([4,2,1,-1,'a'], 4))
print(twister([] , 3))
print(twister([1], 10))