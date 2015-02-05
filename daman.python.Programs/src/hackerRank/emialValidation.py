'''
Created on Feb 4, 2015

@author: daman
'''
import sys
from curses.ascii import isalnum


def validateMail(s):
    l = s.split('@')
    
    if not len(l) == 2:
        #more than one or no '@'char
        return False
    
    userName = l[0]
    l = l[1].split('.')
    
    if not len(l) == 2:
        #more than one or no'.'char
        return False
    
    webName = l[0]
    extension = l[1]
    
    #test end first
    if len(extension) > 3 or len(extension) == 0 :
        return False
    
    if len(webName) == 0:
        return False
    
    for c in webName:
        if not isalnum(c):
            return False
    
    if len(userName) == 0:
        return False
    
    for c in userName:
        if not (isalnum(c) or c == '-' or c == '_'):
            return False
        
    #all validations are done
    return True
    
def filterValidMails(l):
    fl = list(filter(lambda x:validateMail(x),l))
    
    if fl == None:
        sys.stdout.write('Invalid Input')
        
    #now sort the filtered list lexicographically
    rl = sorted(fl)
    
    #sys.stdout.writelines(rl)
    print rl   

def main():
    #sortNumbers(sys.argv[1], sys.argv[data = sys.stdin.readlines()
    fd = []
    
    inp = sys.stdin
    
    nmails = int(inp.readline().rstrip())   
    count = 0
    
    while count < nmails:
        fd.append(inp.readline().rstrip())
        count+=1
    
    filterValidMails(fd)
    
if __name__ == '__main__':
    main()