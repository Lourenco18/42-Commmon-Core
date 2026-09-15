import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from stringutils import reverse_words

def test_reverse_words():
    assert reverse_words("hello world") == "world hello"

def test_reverse_words_single():
    assert reverse_words("solo") == "solo"
