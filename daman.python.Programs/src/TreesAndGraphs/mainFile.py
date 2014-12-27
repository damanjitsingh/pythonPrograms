'''
Created on Dec 26, 2014

@author: dsingh
'''

from TreesAndGraphs.binaryTree import binarySearchTree
from random import randrange

def test_binarySearchTree():
    bst = binarySearchTree(50)
    ##create the tree
    for i in range(10):
        bst.addNode(randrange(1,100))
        
    bst.inOrderTraversal(bst)
    bst.addNode(33)
    print('###########')
    bst.inOrderTraversal(bst)
    bst.searchNode(bst, 33)
    bst.searchNode(bst, 44)
    
test_binarySearchTree()