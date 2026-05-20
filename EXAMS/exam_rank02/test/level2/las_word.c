/*

Assignment name  : last_word
Expected files   : last_word.c
Allowed functions: write
--------------------------------------------------------------------------------

Write a program that takes a string and displays its last word followed by a \n.

A word is a section of string delimited by spaces/tabs or by the start/end of
the string.

If the number of parameters is not 1, or there are no words, display a newline.

Example:

$> ./last_word "FOR PONY" | cat -e
PONY$
$> ./last_word "this        ...       is sparta, then again, maybe    not" | cat -e
not$
$> ./last_word "   " | cat -e
$
$> ./last_word "a" "b" | cat -e
$
$> ./last_word "  lorem,ipsum  " | cat -e
lorem,ipsum$
$>

*/
#include <unistd.h>


int main(int argc, char **argv)
{
    int first_char_word = 0;
    int last_char = 0;

    if (argc == 2)
    {
     
        while (argv[1][last_char])
            last_char++;
        last_char--; 

      
        while (last_char >= 0 && (argv[1][last_char] == ' ' || argv[1][last_char] == '\t'))
            last_char--;

        first_char_word = last_char;
        while (first_char_word >= 0 && argv[1][first_char_word] != ' ' && argv[1][first_char_word] != '\t')
            first_char_word--;

        first_char_word++; 

        
        while (first_char_word <= last_char)
        {
            write(1, &argv[1][first_char_word], 1);
            first_char_word++;
        }
    }

    write(1, "\n", 1);
    return 0;
}
