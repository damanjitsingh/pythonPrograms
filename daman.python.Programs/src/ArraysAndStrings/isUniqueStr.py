'''
Created on Dec 22, 2014
Some of the implementations to find if all the chars in a string are unique(no duplicate characters)
@author: dsingh
'''
def isUnique(s):
    result = False
    newStr = ''
    for char in s:
        if char in newStr:
            return result
        newStr = newStr+char
    result = True
    return result

def isUniqueWithSet(s):
    result = False
    newStr = set()
    for c in s:
        if c in newStr:
            return result
        newStr.add(c)
    result = True
    return result

def removeDuplicateChars(s):
    newStr = ''
    for c in s:
        if c in newStr:
            continue
        newStr = newStr+c
    print(newStr)

def isUniquePythonic(s):
    return len(set(s)) == len(s)
    

print(isUnique('daman'))
print(isUnique('damn'))
print(isUniqueWithSet('daman'))
print(isUniqueWithSet('damn'))
print(isUniquePythonic('daman'))
print(isUniquePythonic('damn'))
removeDuplicateChars('daman')



        
        
