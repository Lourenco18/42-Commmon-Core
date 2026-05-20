def check_temperature(number):
    print(f'testing {number}º')
    try:
        temp = int(number)
    except ValueError as e:
        print("error:", e, "\n")
        return
    if temp < 0:
        print("error, to cold\n")
    elif temp > 40:
        print("error: to hot\n")
    else:
        print("perfect\n")
    return
    
if __name__ == "__main__":
    check_temperature(25)
    check_temperature(100)
    check_temperature(-50)
    check_temperature("abc")
