#include <unistd.h>

void write_num(int number){
    if(number>9){
        write_num(number/10);

    }
    char result = number % 10 + '0';
    write(1, &result,1);
}
int main(){
    int number = 0;
    
    while(number <100){
        number++;
        
        if((number % 5 == 0) && (number % 3 == 0)){
                    write(1, "fizzbuzz",8);
        }else if(number % 3 == 0){
                write(1,"fizz",4);

            }else if(number % 5 == 0 ){
                write(1, "buzz",4);
            }else{
                write_num(number);
            }
            write(1, "\n",1);
    }
    return 0;
}