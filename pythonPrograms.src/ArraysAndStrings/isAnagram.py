'''
Created on Dec 22, 2014
Steps
1.create 2 dictionaries d1 and d2
2.compare the dictionaries
@author: dsingh
'''
def isAnagram(s1,s2):
    sl1 = len(s1)
    sl2 = len(s2)
    
    if sl1 != sl2:
        print('Not anagrams!')
        return
    
    d1 = {}
    d2 = {}
    
    for c in s1:
        key =  ord(c) - ord('a')
        if d1.get(key) == None:
            d1[key] = 1
        else:
            d1[key] = d1[key]+1;
            
    for c in s2:
        key = ord(c) - ord('a') 
        if d2.get(key) == None:
            d2[key] = 1
        else:
            d2[key] = d1[key]+1;
            
    print('dict1 is', d1,'dict2 is', d2)        
            
    for k in d1:
        item1 = d1[k]
        
        if k not in d2:
            print('Not anagrams!')
            return
            
        item2 = d2[k]
        
        if item1 !=  item2:
            print('Not anagrams!')
            return
        
    print('Anagrams!')
    
def isAnagramPythonicWay(s1,s2):
    if sorted(s1) == sorted(s2):
        print('Anagrams!')
    else:
        print('Not anagrams!')
    
isAnagram('army', 'mary')
isAnagram('army', 'dama')
isAnagramPythonicWay('army','mary')
isAnagramPythonicWay('army','dama')

print(sorted('abcdefhg'))
print(sorted(['damjn','damen', 'ajay']))      