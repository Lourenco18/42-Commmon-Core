def Anagram(s1, s2):
    if len(s1) != len(s2):
        return False
    return sorted(s1) == sorted(s2)


print(Anagram("racecar","carrace"))
print(Anagram("Conversation", "Voices rant on"))

