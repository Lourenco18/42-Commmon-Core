def ft_count_harvest_recursive() -> None:
    days = int(input("Days until harvest: "))

    def count(current):
        if current > days:
            return
        print(f"Day {current}")
        count(current + 1)

    count(1)
    print("Harvest time!")


ft_count_harvest_recursive()
