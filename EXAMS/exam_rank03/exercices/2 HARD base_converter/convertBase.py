def convert_base(num, from_base, to_base):
    digits="0123456789ABCDEFGHIJKLMNOPRSTUVWXYZ"
    try:
        if not 2 <= from_base <= 36:
            return  "error"
        if not 2 <= to_base <= 36:
            return "error"
        n = int(num,from_base)
        if n == 0:
            return "0"
        result = ""
        while n:
            result += digits[n % to_base]
            n //=to_base
        return result[::-1]
    except Exception:
        return "error"
# Basic conversions

print(convert_base("1010", 2, 10)        )# "10"
print(convert_base("10", 10, 2)          )# "1010"
print(convert_base("1A", 16, 10))         # "26"
print(convert_base("26", 10, 16)         )# "1A"

# Same base
print(convert_base("123", 10, 10))        # "123"

# Edge cases
print(convert_base("0", 10, 2))           # "0"
print(convert_base("000", 2, 10)         )# "0"

# Larger bases
print(convert_base("ZZZ", 36, 10))        # "46655"
print(convert_base("46655", 10, 36))      # "ZZZ"

# Uppercase handling
print(convert_base("A", 16, 10))          # "10"
print(convert_base("F", 16, 10))          # "15"

# Mixed digits and letters
print(convert_base("1F4", 16, 10))        # "500"
print(convert_base("500", 10, 16))        # "1F4"

# Invalid cases 
print(convert_base("2", 2, 10))           # Error / invalid input
print(convert_base("G", 16, 10))          # Error / invalid input