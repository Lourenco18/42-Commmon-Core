def twister(nums, n) -> list:
    if len(nums) == 0:
        return []

    n = n % len(nums)

    return nums[-n:] + nums[:-n]


print(twister([1, 2, 3, 4, 5], 2))
print(twister([4, 2, 1, -1, 'a'], 4))
print(twister([1, 2, 3], 3))
print(twister([1, 2, 3], 5))
print(twister([1], 10))
print(twister([] , 3))
print(twister([1, 2, 3, 4], -2))

