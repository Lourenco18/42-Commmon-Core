def reverse_words(sentence: str) -> str:
    """Return the sentence with word order reversed."""
    words = sentence.split(" ")
    words.reverse()  # BUG: list.reverse() mutates in place and returns None,
    return words      # so this function returns a list, not the joined string.
