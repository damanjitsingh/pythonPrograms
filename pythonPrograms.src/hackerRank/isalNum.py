'''
Created on Feb 10, 2015

@author: daman
'''
# Enter your code here. Read input from STDIN. Print output to STDOUT

import sys
from curses.ascii import isalnum
from re import findall

def isalNum(l):
    for element in l:
        #length constraint check
        if not len(element) == 10:
            print 'NO'
            continue
        
        #value of first digit check
        if not (element[0] == '7' or element[0] == '8' or element[0] == '9'):
            print 'NO'
            continue
        
        l = findall('[0-9]+',element)
        
        if len(l) == 1 and l[0] == element:
            print 'YES'
        else:
            print 'NO'

def main():
    inp = sys.stdin
    
    numbers = int(inp.readline().rstrip())   
    count = 0
    
    fd = []
    while count < numbers:
        fd.append(inp.readline().rstrip())
        count+=1
        
    isalNum(fd)
        
if __name__ == '__main__':
    main()