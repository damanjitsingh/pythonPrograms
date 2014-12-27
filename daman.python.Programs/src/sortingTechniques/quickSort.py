'''
Created on Dec 26, 2014

@author: dsingh
'''

from random import randrange

class QuickSort(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        self.list = []
        
    def fillList(self,listSize):
        i = 0
        while i < listSize:
            rand = randrange(1,100)
            self.list.append(rand)
            i = i+1
            
    def sort(self):
        l = self.list
        print('Unsorted list: ',l)
        self.quickSort(0,len(l))
        print('sorted list: ',l)
        
    
    #the catch is to set the position of pivot at each round
    def quickSort(self,low,high):
        if low == high:
            return
        
        l = self.list
        mid = (low+high)//2
        pivot = l[mid]
        i = low
        j = mid+1
        
        while i < mid:
            if l[i] > pivot:
                temp = l.pop(i)
                mid -= 1
                l.insert(mid+1, temp)
            else:
                i += 1
            
        while j < high:
            if l[j] < pivot:
                temp = l.pop(j)
                l.insert(mid, temp)
                mid += 1
        
            j += 1
                
        self.quickSort(low, mid)
        self.quickSort(mid+1,high)
        
        
        
        