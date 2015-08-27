'''
Created on Mar 26, 2015

@author: daman
'''
from operator import add
'''
This is my attempt to implement split function
e.g."28+32+++32++39".split will give {'28','32','','','32','','39'}
'''
'''
is there any good and simple way to do that, i feel that the below implementation is error prone and is complex
to understand...lets see..first write your algorithm in comments!!!
Algo:
1.start iterating from the first char of the input string,keep a pointer to the first non target('+') char(p).
In the initial run it is 0
2. once encountered the target char(lets say at position curr) 
which you are looking for, call res.app(p,curr)
3. for each run you need to also check what is there in the immediate prev position of the current char,
if it is the target char then you need to add an empty char to the res string.
'''
def mySplit(s,c):
    #if char or input string is empty simply return from here!
    if s == None or c == None:
        print"Enter valid string/character!"
        return
    
    res = []
    '''
    previousCharIndex is the start point of the non target char index(that is the point
    where the copy needs to start from)
    '''
    currCharIndex = previousCharIndex = 0
    prevChar = s[0]
    
    for ch in s:
        if ch == c:
            if prevChar == c:
                #add empty char
                res.append('')
                previousCharIndex = currCharIndex+1
            else:
                #here copy all the in between chars to the list
                res.append(s[previousCharIndex:currCharIndex])
                previousCharIndex = currCharIndex+1
        
        prevChar = chr
        currCharIndex+=1
    
    ##add the last set of chars
    res.append(s[previousCharIndex:currCharIndex]) 
    print res

if __name__ == '__main__':
    mySplit("28+32+++32++39", '+')
    mySplit("+d+a+m+", '+')
    mySplit('+', '+')
    print reduce(add, map(int, filter(bool, "28+32+++32++39".split("+"))))
        
        
                
           
            
    
    
    