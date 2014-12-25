'''
Created on Dec 23, 2014

@author: dsingh
'''
from sortingTechniques.mergeSort import MergeSort
def test_mergeSort():
    ms = MergeSort()
    ms.fillList(10)
    ms.sort()
    
test_mergeSort()
