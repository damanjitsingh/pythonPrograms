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
def taxicab():
    t = 10000
    cubes, crev = [x**3 for x in range(1,1000)], {}
    # for cube root lookup
    for x,x3 in enumerate(cubes): crev[x3] = x + 1
    
    sums = sorted(x + y for x in cubes for y in cubes if y < x)
    
    idx = 0
    n = 0
    for i in range(1, len(sums)-1):
        if sums[i-1] != sums[i] and sums[i] == sums[i+1]:
            n = sums[i]
            if n<t:
                idx += 1
                print(n)
            else:
                break

if __name__ == '__main__':
    #my_crappy_range(100)
    taxicab()
    