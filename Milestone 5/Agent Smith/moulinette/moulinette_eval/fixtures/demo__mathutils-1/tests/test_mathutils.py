import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mathutils import is_prime

def test_small_primes():
    assert is_prime(2) is True
    assert is_prime(3) is True
    assert is_prime(4) is False

def test_edge_cases():
    assert is_prime(1) is False
    assert is_prime(0) is False
    assert is_prime(-5) is False

def test_larger_prime():
    assert is_prime(97) is True
    assert is_prime(100) is False
