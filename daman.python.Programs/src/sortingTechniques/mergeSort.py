'''
Created on Dec 25, 2014

@author: dsingh
'''
from random import randrange

class MergeSort():
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
        mylist = self.list
        l = len(mylist)
        
        if l == 0:
            print('list is empty, no need to sort!')
            return
        
        print('unsorted list is ', mylist)

        mid = l//2 ##floor division
        self.mergeSort(0,mid)
        self.mergeSort(mid+1,l-1)
        self.merge(0,mid,l-1)
        print('sorted list is ', mylist)
        
    def mergeSort(self,low,high):
        if low == high:
            return
        
        mid = (low + high)//2
        self.mergeSort(low,mid)
        self.mergeSort(mid+1,high)
        self.merge(low,mid,high)
            
    def merge(self,low,mid,high):
        mylist = self.list
        k=mid+1
        i=low
        while i <= mid:
            if mylist[i] > mylist[k]:
                temp = mylist.pop(k)
                mylist.insert(i, temp)
                mid = mid+1 #this took me a while to fix the algorithm
                k=k+1
                if k > high:
                    break
            i=i+1    