
class Plant():
    def __init__(self, name, height, age):
        self.name = name
        self.height = height
        self.age = age

    def get_info(self):
        print(f'Plant: {self.name} ({self.height}cm, {self.age} days)')

    def grow(self):
        self.height+=1
    
    def ageup(self):
        self.age+=1

    def day(self):
        self.grow()
        self.ageup()

class Flower(Plant):
    def __init__(self, name, height, age, color):
        super().__init__(name, height, age)
        self.color = color
        self.type = "Flower"
        
    def bloom(self):
        print(self.name,"is blooming")
    
    def get_info(self):
        print(f'{self.name} ({self.type}): {self.height}cm, {self.age} days, {self.color} color')
        self.bloom()
            
class Tree(Plant):
    def __init__(self, name, height, age,trunk_diameter):
        super().__init__(name, height, age)
        self.trunk_diameter = trunk_diameter
        self.type = "Tree"
        self.shade = 1
        
    def produce_shade(self):
        self.shade = int((self.trunk_diameter *2) + 3)
        print(f'{self.name} provides {self.shade} square meters of shade')
    
    def get_info(self):
        print(f'{self.name} ({self.type}): {self.height}cm, {self.age} days, {self.trunk_diameter}cm diameter')
        self.produce_shade()
        
        
        
class Vegetable(Plant):
    def __init__(self, name, height, age,harvest_season, nutritional_value):
        super().__init__(name, height, age)
        self.harvest_season = harvest_season
        self. nutritional_value =  nutritional_value
        self.type = "Vegetable"
    
    def get_info(self):
        print(f'{self.name} ({self.type}): {self.height}cm, {self.age} days, {self.harvest_season} harvest')
        print(f'{self.name} is rich in {self.nutritional_value}')
    
        
class SecurePlant(Plant):
        def set_height(self,height):
            if height < 0:
                return 0
            else:
                self.__height__= height
                return 1
            
        def set_age(self,age):
            if age < 0:
                return 0
            else:
                self.__age__ = age
                return 1
        
        def get_age(self):
            print(self.age, ' days')
            
        def get_height(self):
            print(self.height,' cm')
        

if __name__ == "__main__":
    count = 0
    plants = [
        Flower("Rose", 25, 30, "red"),
        Tree("Oak", 500, 1825, 50),
        Vegetable("Tomato", 80, 90,"summer", "vitamin C")
    ]
    for plant in plants:
        plant.get_info()
