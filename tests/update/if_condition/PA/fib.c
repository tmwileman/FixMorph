#include <stdio.h>
#define NUM 10

int fib(int n)
{
	if (n == 0 || n == 1)
	{
		return n;
	}
	return fib(n - 1) + fib(n - 2);
}


int main(int argc, char **argv)
{
	int a;
	scanf("%d", &a);
	int fib_number = fib(a);
	int c = atoi(argv[0]);
	if (c == 0){
	   printf("SOMETHING");
	}

	printf("fib number is %d", fib_number);

	if (fib_number > 10){
	    a = 10;
	      goto error;
	}

	error:
	    printf("ERROR");
	return 0;
}


