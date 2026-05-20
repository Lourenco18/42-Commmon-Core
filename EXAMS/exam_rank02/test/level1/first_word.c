#include <unistd.h>


int is_printable(char c){
    if((c >32 && c<127)) return 1;
    return 0;
}
int  is_space_tab(char c){
    if(c == 32 || c ==  9) return 1;
    return 0;
}
int main(int c, char **argv){

    if(c >= 2){
        int i = -1; 
            while(argv[1][++i]){
                while(is_space_tab(argv[1][i])){
                    i++;
                    }
                if(is_printable(argv[1][i])){
                    write(1, &argv[1][i],1);
                    if(!is_printable(argv[1][i +1 ]))
                    return (write(1, "\n",1));
                

                }else break;
                
            }
    }
    write(1,"\n",1);
    return 0;
}