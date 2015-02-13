'''
Created on Feb 11, 2015

@author: daman
'''
import sys

def sortMobileNumbers(l):
    
    numList = []
    for n in l:
        if len(n) == 10:
            numList.append(n)
        elif n[:2] == '91':
            numList.append(n[2:])
        elif n[:3] == '+91':
            numList.append(n[3:])
        elif n[0] == '0':
            numList.append(n[1:])
        else:
            print 'invalid input'
            
    il = sorted(numList)
    
    for n in il:
        print '+91 ' + n[:5] + ' ' + n[5:]
    

def main():
    inp = sys.stdin
    
    numbers = int(inp.readline().rstrip())   
    count = 0
    
    fd = []
    while count < numbers:
        fd.append(inp.readline().rstrip())
        count+=1
        
    sortMobileNumbers(fd)
        
if __name__ == '__main__':
    main()