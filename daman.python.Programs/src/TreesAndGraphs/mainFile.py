'''
Created on Dec 26, 2014

@author: dsingh
'''

from TreesAndGraphs.binaryTree import binarySearchTree
from random import randrange
from TreesAndGraphs import BinarySearchTree_IP
from TreesAndGraphs import treeBasedFunctions

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
    
def test_binarySearchTreeIP():
    mytree = BinarySearchTree_IP.BinarySearchTree()
    mytree[3]="red"
    mytree[4]="blue"
    mytree[6]="yellow"
    mytree[2]="at"

    print(mytree[6])
    print(mytree[2])
    
#test_binarySearchTree()
test_binarySearchTreeIP()
x = treeBasedFunctions()
x.isTreeBalanced()
