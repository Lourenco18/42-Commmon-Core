# include <unistd.h>
char	*ft_strcpy(char *s1, char *s2) 
{
    int i = 0;
    while (s1[i]){
         s2[i] = s1[i];
         i++;
    }
    s2[i] = '\n';
    return (s2);
}
void ft_putstr(char c[] ){
    int i = 0;
    while (c[i]){
        write(1,&c[i],1);
        i++;
    }
    

}

int main(){
    char s1[]= "ola";
    char s2[] = "";

    
    ft_putstr( ft_strcpy(s1, s2));

}