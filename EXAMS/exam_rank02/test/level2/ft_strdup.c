/*

Assignment name  : ft_strdup
Expected files   : ft_strdup.c
Allowed functions: malloc
--------------------------------------------------------------------------------

Reproduce the behavior of the function strdup (man strdup).

Your function must be declared as follows:

char    *ft_strdup(char *src);

*/

#include <stdlib.h>

char    *ft_strdup(char *src){
    char *dup;
    int i = 0;
    int len = 0;
    while(src[len]) len++;
     dup = malloc(sizeof(char)* len + 1);
    if(!dup) return NULL;
    while(src[i]){
        dup[i] = src[i];
        i++;
    }
    dup[i] = '\0';
    return dup;
    
}
