'''
Created on Feb 12, 2015

@author: daman
'''
import sys

def nameDir(nameList):
    nameList = sorted(nameList,key = lambda element:element[2])
    for name in nameList:
        if name[3] == 'M':
            print 'Mr. ' + name[0] + ' ' + name[1]
        else:
            print 'Ms. ' + name[0] + ' ' + name[1]
        

def main():
    inp = sys.stdin
    
    numbers = int(inp.readline().rstrip())   
    count = 0
    
    fd = []
    while count < numbers:
        line = inp.readline().rstrip()
        lineList = line.split(' ')
        fd.append(lineList)
        count+=1
        
    nameDir(fd)
        
if __name__ == '__main__':
    main()