/*

Assignment name  : ft_split
Expected files   : ft_split.c
Allowed functions: malloc
--------------------------------------------------------------------------------

Write a function that takes a string, splits it into words, and returns them as
a NULL-terminated array of strings.

A "word" is defined as a part of a string delimited either by spaces/tabs/new
lines, or by the start/end of the string.

Your function must be declared as follows:

char    **ft_split(char *str);

*/

#include <stdlib.h>
int is_space(char c);

int count_substrings(char const *s)
{
    int i = 0;
    int word_count = 0;
    if (!s)
        return 0;
    while (s[i])
    {
        while (s[i] && is_space(s[i]))
            i++;
        if (!s[i])
            break;
        word_count++;
        while (s[i] && !is_space(s[i]))
        {
            i++;
        }
    }
    return (word_count);
}
static void free_result(char **res, int j)
{
    while (j-- > 0)
        free(res[j]);
}
static char *alloc_subs(const char *s, int start, int end)
{
    int i = 0;
    int len = 0;
    char *str;
    len = end - start;
    str = malloc(len + 1);
    if (!str)
        return 0;
    while (start < end)
    {
        str[i++] = s[start++];
    }
    str[i] = '\0';
    return str;
}

static int p_substring(const char *s, char **res, int substrings)
{
    int j = 0;
    int start = 0;
    int end = 0;
    while (j < substrings)
    {
        while (s[start] && is_space(s[start]))
        {
            start++;
        }
        end = start;
        while (s[end] && !is_space(s[end]))
        {
            end++;
        }
        res[j] = alloc_subs(s, start, end);
        if (!res[j])
            return (free_result(res, j), 0);
        start = end;
        j++;
    }
    res[j] = 0;
    return 1;
}

int is_space(char c)
{
    return (c == ' ' || c == '\t' || c == '\n');
}

char **ft_split(char *str)
{
    int substrings;
    char **result;

    if (!str)
        return 0;
    substrings = count_substrings(str);
    result = malloc((substrings + 1) * sizeof(char *));
    if (!result)
        return 0;
    if (!p_substring(str, result, substrings))
    {
        free_result(result, substrings);
        return (0);
    }
    return result;
}