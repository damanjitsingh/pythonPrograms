'''
Created on Dec 25, 2015

@author: damanjits
'''

from random import *
#create a list of the random numbers 
l = randrange(100)
mylist = []
i=1
while(i<=l):
    mylist.append(randrange(pow(2, 31)-1))
    i+=1
    
#now select a random set out of mylist
subsetlen = randrange(l)
subset = []
i=1
while(i<=subsetlen):
    subset.append(mylist[randrange(l)])
    i+=1
   
#finally print the sorted list
subset.sort()
print(subset)
 
    