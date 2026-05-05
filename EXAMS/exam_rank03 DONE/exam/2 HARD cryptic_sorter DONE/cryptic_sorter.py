def cryptic_sorter(tlist):
    def vogais(s):
        return sum(c in "aeiou" for c in s.lower())
    result = sorted(tlist, key=lambda s:(len(s),s.lower(),s.isupper(), vogais(s)))
    return result

print(cryptic_sorter(["apple", "bat", "car", "ae", "b"]))
words = ["bat", "cat", "ant"]
print(cryptic_sorter(words)) 
print(cryptic_sorter(["BBB", "bbb", "ccc", "CCC"]))