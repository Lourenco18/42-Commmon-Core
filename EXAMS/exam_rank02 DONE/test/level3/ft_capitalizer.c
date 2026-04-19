#include <unistd.h>

int is_alpha(char c)
{
    return ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'));
}

int is_space(char c)
{
    return (c == ' ' || (c >= '\t' && c <= '\r'));
}

char to_lower(char c)
{
    if (c >= 'A' && c <= 'Z')
        return (c + 32);
    return c;
}

char to_upper(char c)
{
    if (c >= 'a' && c <= 'z')
        return (c - 32);
    return c;
}

int main(int argc, char **argv)
{
    int i;
    int j;

    if (argc < 2)
    {
        write(1, "\n", 1);
        return 0;
    }

    i = 1;
    while (i < argc)
    {
        j = 0;
        while (argv[i][j])
        {
            if ((j == 0 || is_space(argv[i][j - 1])) && is_alpha(argv[i][j]))
            {
                char c = to_upper(argv[i][j]);
                write(1, &c, 1);
            }
            else
            {
                char c = to_lower(argv[i][j]);
                write(1, &c, 1);
            }
            j++;
        }
        write(1, "\n", 1);
        i++;
    }
    return 0;
}
