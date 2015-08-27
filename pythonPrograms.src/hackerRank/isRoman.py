'''
Created on Feb 11, 2015

@author: daman
'''

import sys
from curses.ascii import isalnum
import re

def isRoman(s):
    
    #tens character can be repeated up to 3 times
    if re.search(r'I{4,}',s) or re.search(r'X{4,}',s) or re.search(r'C{4,}',s) or re.search(r'M{4,}',s):
        #print 'error tens char issue'
        print False
        return
    
    #fives characters cannot be repeated
    if re.search(r'V{2,}', s) or re.search(r'L{2,}', s) or re.search(r'D{2,}', s):
        #print 'error due to fives character'
        print False
        return
    
    #certain chars cannot be present before others
        if re.search(r'IC', s):
            print False
            return
    
    l = re.findall('[IVXLCDM]+',s)
        
    if len(l) == 1 and l[0] == s:
        print 'True'
    else:
        print 'False'

def main():
    inp = sys.stdin
    isRoman(inp.readline().rstrip())
        
if __name__ == '__main__':
    main()