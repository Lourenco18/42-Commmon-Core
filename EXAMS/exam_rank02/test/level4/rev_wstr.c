/*

Assignment name  : rev_wstr
Expected files   : rev_wstr.c
Allowed functions: write, malloc, free
--------------------------------------------------------------------------------

Write a program that takes a string as a parameter, and prints its words in
reverse order.

A "word" is a part of the string bounded by spaces and/or tabs, or the
begin/end of the string.

If the number of parameters is different from 1, the program will display
'\n'.

In the parameters that are going to be tested, there won't be any "additional"
spaces (meaning that there won't be additionnal spaces at the beginning or at
the end of the string, and words will always be separated by exactly one space).

Examples:

$> ./rev_wstr "You hate people! But I love gatherings. Isn't it ironic?" | cat -e
ironic? it Isn't gatherings. love I But people! hate You$
$>./rev_wstr "abcdefghijklm"
abcdefghijklm
$> ./rev_wstr "Wingardium Leviosa" | cat -e
Leviosa Wingardium$
$> ./rev_wstr | cat -e
$
$>

*/
#include <unistd.h>
#include <stdio.h>
int is_space(char c)
{
    if (c == ' ' || (c >= 9 && c <= 13))
        return 1;
    return 0;
}

int find_end(char **argv)
{
    int i = 0;
    while (argv[1][i])
    {
        i++;
    }
    return i;
}
void write_word(char **argv, int start, int end)
{
    while (start <= end)
    {
        write(1, &argv[1][start], 1);
        start++;
    }
}
int main(int c, char **argv)
{
    int is_word = 0;
    int start_word = 0;
    int end_word = 0;
    if (c == 2)
    {
        int end = find_end(argv) - 1;
        while (end >= 0)
        {
            if (!is_space(argv[1][end]))
            {
                end_word = end;
                while (end >= 0 && !is_space(argv[1][end]))
                    end--;
                start_word = end + 1;
                write_word(argv, start_word, end_word);
                if (end >= 0)
                    write(1, " ", 1);
            }
            end--;
        }
    }
    write(1, "\n", 1);
    return 0;
}