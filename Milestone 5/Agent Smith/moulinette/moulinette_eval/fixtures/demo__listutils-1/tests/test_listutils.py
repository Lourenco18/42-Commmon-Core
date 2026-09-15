import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from listutils import dedupe_preserve_order

def test_dedupe_order():
    assert dedupe_preserve_order([3, 1, 3, 2, 1]) == [3, 1, 2]

def test_dedupe_empty():
    assert dedupe_preserve_order([]) == []
