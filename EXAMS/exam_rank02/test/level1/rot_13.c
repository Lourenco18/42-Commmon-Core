#include <unistd.h>
int is_alpha(char c){
    if((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'))
        return 1;
    return 0;
}

int main(int c, char **argv){
    char result;
    int number = 13;
    if(c == 2){
        int i = -1;
        while(argv[1][++i]){
            if(is_alpha(argv[1][i])){
               if((argv[1][i] > 'M'  && argv[1][i] <= 'Z')|| (argv[1][i] > 'm' && argv[1][i] <= 'z')){
                    result = argv[1][i] - number;
                   write(1, &result, 1);

               }else{
                   result = argv[1][i] + number;
                   write(1, &result, 1);
               }
               
        
            }else{
                write(1, &argv[1][i], 1);
        }
    }
    }
    write(1, "\n", 1);
    return 0;
}