# Enter your code here. Read input from STDIN. Print output to STDOUT
'''
Created on Feb 10, 2015

@author: daman
'''
# Enter your code here. Read input from STDIN. Print output to STDOUT

import sys
from curses.ascii import isalnum
from re import findall

def isRoman(s):
    
    l = findall('[IVXLCDM]+',s)
        
    if len(l) == 1 and l[0] == s:
        print 'YES'
    else:
        print 'NO'

def main():
    inp = sys.stdin
    isRoman(inp.readline().rstrip())
        
if __name__ == '__main__':
    main()