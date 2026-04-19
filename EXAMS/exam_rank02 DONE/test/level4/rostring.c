/*
Assignment name  : rostring
Expected files   : rostring.c
Allowed functions: write, malloc, free
--------------------------------------------------------------------------------

Write a program that takes a string and displays this string after rotating it
one word to the left.

Thus, the first word becomes the last, and others stay in the same order.

A "word" is defined as a part of a string delimited either by spaces/tabs, or
by the start/end of the string.

Words will be separated by only one space in the output.

If there's less than one argument, the program displays \n.

Example:

$>./rostring "abc   " | cat -e
abc$
$>
$>./rostring "Que la      lumiere soit et la lumiere fut"
la lumiere soit et la lumiere fut Que
$>
$>./rostring "     AkjhZ zLKIJz , 23y"
zLKIJz , 23y AkjhZ
$>
$>./rostring "first" "2" "11000000"
first
$>
$>./rostring | cat -e
$
$>

*/
#include <unistd.h>

int is_space(char c)
{
    if (c == ' ' || (c >= 9 && c <= 13))
        return 1;
    return 0;
}

int len_all(char *str)
{
    int len = 0;
    while (str[len])
        len++;
    return len;
}

int is_empty(char **argv)
{
    int i = 0;
    while (argv[1][i])
    {
        if (!is_space(argv[1][i]))
            return 0;
        i++;
    }
    return 1;
}

void find_string(char **argv, int *start_first_word, int *end_first_word)
{
    int i = 0;
    int temp = 0;

    while (argv[1][i])
    {
        if (!is_space(argv[1][i]))
        {
            *start_first_word = i;
            break;
        }
        i++;
    }

    temp = *start_first_word;
    while (argv[1][temp])
    {
        if (is_space(argv[1][temp]))
        {
            *end_first_word = temp - 1;
            return;
        }
        temp++;
    }

    *end_first_word = temp - 1;
}

int main(int c, char **argv)
{
    if (c != 2)
    {
        write(1, "\n", 1);
        return 0;
    }

    if (len_all(argv[1]) == 0 || is_empty(argv))
    {
        write(1, "\n", 1);
        return 0;
    }

    int end_first_word = 0;
    int start_first_word = 0;
    find_string(argv, &start_first_word, &end_first_word);

    int end = end_first_word + 1;
    int word = 0;
    int printed = 0;

    while (argv[1][end])
    {
        if (is_space(argv[1][end]))
        {
            word = 0;
        }
        else
        {
            if (word == 0)
            {
                if (printed)
                    write(1, " ", 1);
                printed = 1;
            }
            word = 1;
            write(1, &argv[1][end], 1);
        }
        end++;
    }

    if (printed)
        write(1, " ", 1);

    while (start_first_word <= end_first_word)
    {
        write(1, &argv[1][start_first_word], 1);
        start_first_word++;
    }

    write(1, "\n", 1);
    return 0;
}
