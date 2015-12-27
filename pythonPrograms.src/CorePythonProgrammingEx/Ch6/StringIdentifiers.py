'''
Created on Dec 26, 2015

@author: damanjits
'''
'''
This application checks for valid python identifiers and returns invalid if 
1.identifier mathches names of reserved words in python
2.first char of identifier is not alphabetic+'_'
3.rest of the chars are not alphanumeric+'_'
'''

from keyword import kwlist
import string

alphas = string.ascii_letters + '_'
nums = string.digits

def identifierTest():
    name = input("enter the name to be tested for valid python identifier\n")
    l = len(name)
    if l == 1:
        if name in alphas:
            print("valid identifier!")
        else:
            print("invalid:first symbol must be alphabetic")
    elif l > 1:
        if name in kwlist:
            print("invalid: identifier cannot be a reserved name")
        elif name[0] not in alphas:
            print("invalid:first symbol must be alphabetic")
        else:
            alphanums = alphas + nums
            for otherchar in name[1:]:
                if otherchar not in alphanums:
                    print("invalid: remaining chars must be alphanumeric")
                    break
            else:
                print("valid identifier!")
    else:
        print("invalid: identifier cannot be an empty string")
                
                
if __name__ == '__main__':
    identifierTest()
        