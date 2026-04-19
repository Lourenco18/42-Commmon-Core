#include    <unistd.h>
#include    <stdio.h>

int is_alpha(char c){
    if((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'))
        return 1;
    return 0;
}
int is_lower(char c){
    if(c >= 'a' && c <= 'z')
        return 1;
    return 0;
}
int main(int c, char **argv){
    int number = 0;
    if(c == 2){
        
        int i = -1;
        while(argv[1][++i]){
            
            if(is_alpha(argv[1][i])){
                
                if(is_lower(argv[1][i])){
         
                     number = argv[1][i] - 97 +1;
                }else{
                    number = argv[1][i] - 65 +1;
                }
                while(number > 0){
                    write(1, &argv[1][i], 1);
                    number--;
                }
            }else{
               
                write(1, &argv[1][i], 1);
            }
        }
    }
    write(1, "\n", 1);
    return 0;

}