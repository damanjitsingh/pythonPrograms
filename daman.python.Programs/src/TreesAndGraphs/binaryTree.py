'''
Created on Dec 26, 2014

@author: dsingh
'''
from TreesAndGraphs.__init__ import errorCodes

class binarySearchTree():
    '''
    classdocs
    '''
    INITIALVALUE = 9999

    def __init__(self,value):
        '''
        Constructor
        '''
        self.value = value
        self.leftChild = errorCodes.NULL
        self.rightChild = errorCodes.NULL
        
    def searchNode(self,currentNode,value):
        if currentNode == errorCodes.NULL:
            print('No node with value', value,'is found')
            return errorCodes.NULL
        
        currentNodeValue = currentNode.value
        
        if currentNodeValue == value:
            print('Node found')
            return currentNode
        
        if value < currentNodeValue:
            currentNode = currentNode.leftChild
        elif value > currentNodeValue:
            currentNode = currentNode.rightChild
            
        self.searchNode(currentNode,value)
        
    def addNode(self,value):
        currentNode = self
        parentNode  = self
        
        while not currentNode == errorCodes.NULL:
            parentNode = currentNode
            if value > parentNode.value:
                currentNode = parentNode.rightChild
            elif value < parentNode.value:
                currentNode = parentNode.leftChild
            else:
                print('Node already exists!!')
                return
                
                
        newNode = binarySearchTree(value)
        if value > parentNode.value:
            parentNode.rightChild = newNode
        else:
            parentNode.leftChild = newNode
            
    def inOrderTraversal(self,node):
        if node == errorCodes.NULL:
            return
        
        self.inOrderTraversal(node.leftChild)
        print(node.value,'<-->')
        self.inOrderTraversal(node.rightChild)
        
        
                
             
            
        
        