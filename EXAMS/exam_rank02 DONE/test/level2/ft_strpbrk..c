/*

Assignment name	: ft_strpbrk
Expected files	: ft_strpbrk.c
Allowed functions: None
---------------------------------------------------------------

Reproduce exactly the behavior of the function strpbrk
(man strpbrk).

The function should be prototyped as follows:

char	*ft_strpbrk(const char *s1, const char *s2);

*/
char	*ft_strpbrk(const char *s1, const char *s2){
    if(!s1||!s2) return 0;
    while(*s1){
        int i = -1;
        while(s2[++i]){
if(*s1 == s2[i]) return (char *) s1;
        }
            
        s1++;
    }
    return 0;
}

