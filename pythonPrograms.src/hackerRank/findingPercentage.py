'''
Created on Feb 9, 2015

@author: daman
'''
import sys


def getAverage():
    inp = sys.stdin
    
    nStudents = int(inp.readline().rstrip())
    
    if  not nStudents in range(2,11):
        print 'error'
    
 
    count = 0
    myDic = {}
    
    while count < nStudents:
        line = inp.readline().rstrip()
        student,p,c,m = line.split(' ')
        mySum = float(p)+float(c)+float(m)
        avg = mySum/3.0
        myDic[student] = avg
        count+=1
        
    targetStudent = inp.readline().rstrip()
    
    print("%.2f" %myDic[targetStudent])

def main():
    getAverage()
    
if __name__ == '__main__':
    main()