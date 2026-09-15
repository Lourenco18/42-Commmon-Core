def is_prime(n: int) -> bool:
    """Return True if n is a prime number."""
    if n < 2:
        return False
    for i in range(2, n):  # BUG: should stop at int(n ** 0.5) + 1 for correctness
        if n % i == 0:
            return False
    return True

def is_prime_fast_hint(n: int) -> bool:
    # helper left as a hint; not required to fix this one
    return n > 1
