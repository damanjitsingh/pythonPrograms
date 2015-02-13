'''
Created on Feb 10, 2015

@author: daman
'''

# Enter your code here. Read input from STDIN. Print output to STDOUT
import sys

def main():
    inp = sys.stdin
    mystr = inp.readline().rstrip()
    substr = inp.readline().rstrip()
    
    a,b,c = mystr.partition(substr)
    #get the last char of substring, to check for consecutive substrings 
    lc = substr[-1:]
    substrCount = 0
    while not len(b) == 0:
        substrCount+=1
        c = lc+c
        a,b,c = c.partition(substr)
        
    print substrCount
    
if __name__ == '__main__':
    main()