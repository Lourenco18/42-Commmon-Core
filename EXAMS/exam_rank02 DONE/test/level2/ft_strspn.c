/*

Assignment name	: ft_strspn
Expected files	: ft_strspn.c
Allowed functions: None
---------------------------------------------------------------

Reproduce exactly the behavior of the strspn function 
(man strspn).

The function should be prototyped as follows:

size_t	ft_strspn(const char *s, const char *accept);

*/
size_t	ft_strspn(const char *s, const char *accept)
{
	size_t coun = 0;
    int found;
    int i;
    while(*s){
        found = 0;
        i = -1;
        while(accept[++i]){
            if(accept[i] == *s){
                found = 1;
                break;
            }

        }
        if(!found) break;
        count++;
        s++;
    }
    return count;
}


