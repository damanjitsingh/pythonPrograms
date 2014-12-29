'''
Created on Dec 27, 2014

@author: dsingh
'''
from StacksAndQueues.stackClass import Stack
from TreesAndGraphs.BinarySearchTree_IP import BinarySearchTree, TreeNode

class treeBasedFunctions:
    def __init__(self):
        pass
    
    
    '''
    Problem statement 4.1
    '''
    def isTreeBalanced(self,rootNode):
        if (self.maxDepth(rootNode) - self.minDepth(rootNode)) > 1:
            print('tree is not balanced!')
        else:
            print('tree is balanced!')
            
    def _maxDepth(self,node):
        if node == None:
            return 0;
        return 1 + max(self.maxDepth(node.leftChild), self.maxDepth(node.rightChild))
    
    def _minDepth(self,node):
        if node == None:
            return 0;
        return 1 + min(self.minDepth(node.leftChild), self.minDepth(node.rightChild))
    
    '''
    Problem statement 4.2
    '''
    def isPathBetweenTwoNodes(self,rootNode,node1,node2):
        if self._isRoute(node1,node2):
            return True
        else:
            return False
        
        if self._isRoute(node2,node1):
            return True
        else:
            return False
    
    def _pushAllChildrenToStack(self,stack,nodesList):
        for child in nodesList:
            stack.push(child)
        
    
    def _isRoute(self,src,dest):
        if src == None or dest == None:
            return False
        
        children = src.getChildren()
        stack = Stack()
        
        self._pushAllChildrenToStack(stack,children)
            
        #now initial stack is ready
        while not stack.isEmpty():
            node = stack.pop()
            if node.key == dest.key:
                return True
            if node.hasChildren:
                c = node.getChildren()
                self._pushAllChildrenToStack(stack, c)
            
        return False
    
    '''
    Problem statement 4.3
    '''            
    def createMinHeightBST(self,sortedList):
        size = len(sortedList)
        bst = BinarySearchTree()
        
        if size == 0:
            print('invalid list!')
            return None
        elif size == 1:
            print('min height of tree is 1')
            value = sortedList[0]
            bst.put(0, value)
        else:
            mid = size//2
            val = sortedList[mid]
            bst.put(mid,val)
            rootNode = bst.root
            rootNodeLeft = self._getSubtree(sortedList,0,mid-1)
            rootNodeRight = self._gettSubtree(sortedList,mid+1,size-1)
            rootNode.leftChild = rootNodeLeft
            rootNode.rightChild = rootNodeRight
            rootNodeLeft.parent = rootNode
            rootNodeRight.parent = rootNode
            
            return rootNode
        
        
    def _getSubtree(self,sortedList,low,high):
        mid = (low+high)//2
        node = TreeNode(mid,sortedList[mid])
        
        if low == high:
            ##create a node and simply return
            return node
        
        leftSubtree = self._getSubtree(sortedList, low, mid-1)
        rightSubtree = self._getSubtree(sortedList, mid+1, high)
        node.leftChild = leftSubtree
        node.rightChild = rightSubtree
        leftSubtree.parent = node
        rightSubtree.parent = node
        
        return node
    
    '''
    Problem statement 4.4
    '''
    def linkedListAtEachDepthOfBST(self,rootNode):
        lst = linkedList(rootNode.payload)
        llst = linkedList(lst)
        
        for linkList in llst:
            newLL = linkedList()
            
            for element in linkList:
                if not element.hasAnyChildren():
                    continue
                
                #atleast one child is there
                if element.hasLeftChild():
                    leftChildNode = element.leftChild
                    newLL.add(leftChildNode)
                if element.hasRightChild():
                    rightChild = element.rightChild
                    newLL.add(rightChild)
             
            if newLL.getSize > 0:
                llst = linkedList(newLL)
        
        return llst
                     
            
        
        
        
            
            
        
        
    
    