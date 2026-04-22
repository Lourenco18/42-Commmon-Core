def convert_base(num: str, from_base: int, to_base: int) -> str:
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    try:
        if not 2 <= from_base <= 36:
            return "ERROR"
        if not 2 <= to_base <= 36:
            return "ERROR"
        
        n = int(num, from_base)
        if n == 0:
            return "0"
        
        res = ""
        while n:
            res += digits[n % to_base]
            n //= to_base
        
        return res[::-1]
    except Exception:
        return "ERROR"

print(convert_base("Ff", 16, 10)) 
print(convert_base("00FF", 16, 2))
print(convert_base("z", 36, 10))
print(convert_base("0000", 7, 10))
print(convert_base("0001", 2, 10))
print(convert_base("1010", 2, 16))
print(convert_base("133742", 8, 42))