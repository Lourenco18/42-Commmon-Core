def ft_hello_garden():
    print("hello")


def ft_harvest_total():
    d1 = int(input("day1"))
    d2 = int(input("day2"))
    d3 = int(input("day3"))
    result = d1 + d2 + d3
    print(f'total {result}')


def ft_plot_area():
    len = int(input("l:"))
    w = int(input("w:"))
    result = len * w
    print(f'area:{result}')


def ft_plant_age():
    age = int(input("age:"))
    if age > 60:
        print("ready")
        exit()
    print("not ready")


def ft_count_harvest_iterative():
    days = int(input("days:"))
    for i in range(days):
        print(f'day {i+1}')


def ft_count_harvest_recursive():
    days = int(input("days:"))

    def c(count):
        if count > days:
            return
        print(f'day {count}')
        c(count+1)

    c(1)


# ft_hello_garden()
# ft_harvest_total()
# ft_plot_area()
# ft_plant_age()
# ft_count_harvest_iterative()
# ft_count_harvest_recursive()
