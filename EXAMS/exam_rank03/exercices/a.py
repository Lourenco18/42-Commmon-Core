def Sort_string(tlist):
    def vogais(s):
        return sum(c in "aeiou" for c in s)
    result = sorted(tlist, key=lambda s:(len(s),s.lower(), s.isupper(), vogais(s)))
    return result

print(Sort_string(["apple", "bat", "car", "ae", "b"]))
# ['b', 'ae', 'bat', 'car', 'apple']
