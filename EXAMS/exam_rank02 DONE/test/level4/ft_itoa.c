/*

Assignment name  : ft_itoa
Expected files   : ft_itoa.c
Allowed functions: malloc
--------------------------------------------------------------------------------

Write a function that takes an int and converts it to a null-terminated string.
The function returns the result in a char array that you must allocate.

Your function must be declared as follows:

char	*ft_itoa(int nbr);

*/

#include <stdlib.h>

int int_len(long int n)
{

    int i = 0;
    if (n == 0)
        return 1;
    if (n < 0)
    {
        i++;
        n *= -1;
    }
    while (n > 0)
    {
        i++;
        n = n / 10;
    }
    return i;
}

char *ft_itoa(int nbr)
{
    char *str;
    long int n = nbr;
    int len = int_len(n);
    str = (char *)malloc(len + 1);
    if (!str)
        return (NULL);
    str[len] = '\0';
    if (n < 0)
    {
        str[0] = '-';
        n *= -1;
    }
    while (len--)
    {
        if (str[len] == '-')
            break;
        str[len] = (n % 10) + '0';
        n /= 10;
    }
    return (str);
}
