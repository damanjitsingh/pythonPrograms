'''
Created on Jun 30, 2015

@author: damanjits
'''
##########################################################################################
("check how the file is read, focus on the 'r' char")
def getHex():
    with open(r'C:\Users\damanjits\Desktop\hex.txt') as fp:
        for line in fp:
            print(line.split()[19:35])



##########################################################################################
#http://stackoverflow.com/questions/11011756/is-there-any-pythonic-way-to-combine-two-dicts-adding-values-for-keys-that-appe/11011846#11011846      
def addDict(d1,d2):
    result = d1.copy()
    for k,v in d2.items():
        if k in d1:
            result[k] = d1[k]+v
        else:
            result[k] = v 
    print(result,'\n')
    
def addDictPythonic(d1,d2):
    from collections import Counter
    x = Counter(d1)
    y = Counter(d2)
    print(x+y,"\n")
##########################################################################################
def my_crappy_range(N):
    i = 0
    while i < N:
        yield i
        i += 1
    return   
##########################################################################################
        

if __name__ == '__main__':
    my_crappy_range(100)
    