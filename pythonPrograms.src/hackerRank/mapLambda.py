'''
Created on Feb 12, 2015

@author: daman
'''
import sys

fib = []

def Fib(n):
    if n == 0:
        fib.append(0)
    elif n == 1:
        fib.append(1)
    else:
        fib.append(fib[n-1] + fib[n-2])
    
def cube(n):
    return n*n*n

def cubeFib(n):
    i = 0
    for i in range(0,n):
        Fib(i)
    
    print fib
    #print [num*num*num for num in fib]
    print list(map(cube, fib))
    


def main():
    inp = sys.stdin
    cubeFib(int(inp.readline().rstrip()))
        
if __name__ == '__main__':
    main()