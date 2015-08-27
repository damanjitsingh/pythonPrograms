'''
Created on Feb 9, 2015

@author: daman
'''
import sys

def main():
    #sortNumbers(sys.argv[1], sys.argv[data = sys.stdin.readlines()
    fd = []
    
    inp = sys.stdin
    x = int(inp.readline().rstrip())
    y = int(inp.readline().rstrip())
    z = int(inp.readline().rstrip())
    n = int(inp.readline().rstrip())

    
    #result = []
    '''
    for i in range(0,x+1):
        for j in range(0,y+1):
            for k in range(0,z+1):
                localList = [i,j,k]
                if not sum(localList) == n:
                    result.append(localList)
    '''
    #below is the pythonic way of writing the above commented code!!!!
    result = [[i,j,k] for i in range(0,x+1) for j in range(0,y+1) for k in range(0,z+1) if not sum([i,j,k]) == n]
    print result
                
    
if __name__ == '__main__':
    main()