'''
Created on Dec 22, 2014

@author: dsingh
'''

#this will check if s is substring of d 
def isSubstring(s,d):
    if d.find(s) == -1:
        return False
    else:
        return True
    
#this will check if s2 is rotation of s1, e.g. waterbottle is rotation of erbottlewat     
def isRotationOf(s1,s2):
    s3 = s2+s2
    if isSubstring(s1, s3):
        print(s2,'is a rotation of',s1)
    else:
        print(s2,'is not a rotation of',s1)
        
        
isRotationOf('waterbottle', 'erbottlewat')
isRotationOf('waterbottle', 'terbottlewat')