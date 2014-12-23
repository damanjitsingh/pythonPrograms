'''
Created on Dec 22, 2014

@author: dsingh
'''
def revStr(s):
    result = ''
    length = len(s)
    
    while length>0:
        result = result + s[length-1]
        length=length-1
        
    print('reverse of', s,'is', result);
    
def revStrPythonic(s):
    print(s[::-1])
    

#call the function
revStr('damanjitsingh\0at')
revStrPythonic('daman')

