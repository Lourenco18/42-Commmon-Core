/*

Assignment name  : is_power_of_2
Expected files   : is_power_of_2.c
Allowed functions: None
--------------------------------------------------------------------------------

Write a function that determines if a given number is a power of 2.

This function returns 1 if the given number is a power of 2, otherwise it returns 0.

Your function must be declared as follows:

int	    is_power_of_2(unsigned int n);

*/


int elevado(int base, int n){
    int result = 1;
    if(n == 0 )return 1;
    while(n > 0){
        result = result* base;
        n--;
    }
    return result;
}

int	    is_power_of_2(unsigned int n){
    int number = 0;
    while(elevado(2,number) <= n){
        if(elevado(2,number) == n){
            return 1;
        }
        number++;
    }
    return 0;
    
}


