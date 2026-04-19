int ft_strlen(char s[]){
    int i = 0;
    while(s[i]){
        i++;
    }
    return i;

}
#include <stdio.h>

int main(){
    printf("%d\n", ft_strlen("Hello"));
    return 0;}