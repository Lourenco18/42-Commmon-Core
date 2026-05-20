/*

Assignment name  : rev_print
Expected files   : rev_print.c
Allowed functions: write
--------------------------------------------------------------------------------

Write a program that takes a string, and displays the string in reverse
followed by a newline.

If the number of parameters is not 1, the program displays a newline.

Examples:

$> ./rev_print "zaz" | cat -e
zaz$
$> ./rev_print "dub0 a POIL" | cat -e
LIOP a 0bud$
$> ./rev_print | cat -e
$

*/
#include <unistd.h>
int length(char *s){
    int i =0;
    while(s[i])
        i++;
    return i;
}

int main(int c, char **argv){
    int len = 0;
    if(c==2){
        len = length(argv[1]) - 1 ;
        while(len>=0){
            write(1, &argv[1][len], 1);
            len--;
        }

    }
    write(1, "\n", 1);
    return 0;

}
