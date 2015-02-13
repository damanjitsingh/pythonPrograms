'''
Created on Feb 9, 2015

@author: daman
'''
import sys

def symmDifference(l1,l2):
    s1 = set(l1)
    s2 = set(l2)
    
    u = s1.union(s2)
    i = s1.intersection(s2)
    
    result = u.difference(i)
    result = sorted(result)
    
    for e in result:
        print e
        
def main():
    inp = sys.stdin
    
    ls1 = int(inp.readline().rstrip())
    lis1 =  (inp.readline().rstrip()).split()
    intLis1 = list(map(int,lis1))
    
    ls3 = int(inp.readline().rstrip())
    lis2 =  (inp.readline().rstrip()).split()
    intLis2 = list(map(int,lis2))
    
    symmDifference(intLis1, intLis2)
    
if __name__ == '__main__':
    main()
    
    