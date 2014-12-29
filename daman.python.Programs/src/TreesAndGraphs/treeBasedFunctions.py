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
            
    def _maxDepth(self,n):
        if n == None:
            return 0;
        return 1 + max(self.maxDepth(n.leftChild), self.maxDepth(n.rightChild))
    
    def _minDepth(self,n):
        if n == None:
            return 0;
        return 1 + min(self.minDepth(n.leftChild), self.minDepth(n.rightChild))
    
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
            n = stack.pop()
            if n.key == dest.key:
                return True
            if n.hasChildren:
                c = n.getChildren()
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
        n = TreeNode(mid,sortedList[mid])
        
        if low == high:
            ##create a n and simply return
            return n
        
        leftSubtree = self._getSubtree(sortedList, low, mid-1)
        rightSubtree = self._getSubtree(sortedList, mid+1, high)
        n.leftChild = leftSubtree
        n.rightChild = rightSubtree
        leftSubtree.parent = n
        rightSubtree.parent = n
        
        return n
    
    '''
    Problem statement 4.4
    '''
    def linkedListAtEachDepthOfBST(self,rootNode):
        lst = [rootNode]
        llst = [lst]
        
        for linkList in llst:
            newLL = []
            
            for element in linkList:
                if not element.hasAnyChildren():
                    continue
                
                #at least one child is there
                if element.hasLeftChild():
                    leftChildNode = element.leftChild
                    newLL.append(leftChildNode)
                if element.hasRightChild():
                    rightChild = element.rightChild
                    newLL.append(rightChild)
             
            if newLL.getSize > 0:
                llst.append(newLL)
        
        return llst
    
    '''
    Problem statement 4.5
    '''
    def nextNodeTraversal(self, n):
        if n == None:
            print('Invalid n!')
            return
        
        #if currentNode has right child
        if n.hasRightChild():
            #the left most n of this subtree will be visisted next
            rc = n.rightChild
            while not rc.hasleftChild() == None:
                rc = rc.leftChild
            return rc
        
        #get the parent of current n
        p = n.parent
        if p == None:
            return None
        elif p.leftChild == n:
            #i.e. current n is at the left of its parent
            return p
        else:
            #if current n is at right of its parent then go up till you find the parentNode(p) is at left of its parentNode(pp), the next n will then be pp
            nextNode = p
            while not nextNode == None:
                pp = p.parent
                if pp.leftChild == p:
                    return pp
                nextNode = pp
                
            return None
        
    
    '''
    Problem statement 4.6
    '''
    def firstCommonAncestor(self,node1,node2):
        if node1 == None or node2 == None:
            print('enter valid nodes!')
            return 
        
        if node1.key == node2.key:
            return node1.parent
        
        bst = BinarySearchTree()
        if not bst._get(node2.key, node1) == None:
            #node2 is present in subtree which is under node1
            return node1
        if not bst._get(node1.key, node2) == None:
            return node2
        
        #At this point node1 and node2 are present in separate branches,so they must have a unique common ancestor
        p = node1.parent
        pl = []
        while not p == None:
            pl.append(p)
            p = p.parent
        
        p2 = node2.parent
        
        while not p2 in pl:
            p2 = p2.parent
            
        return p2
    
    '''
    Problem statement 4.7
    '''
    def isT2SubtreeOfT1(self,t1,t2):
        #assume t1 and t2 are valid trees
        
        t1Root = t1.root
        t2Root = t2.root
        
        if t1Root.value == t2Root.value:
            if self._isSameTree(t1Root.leftChild,t2Root.leftChild) and self._isSameTree(t1Root.rightChild,t2Root.rightChild):
                return True
            
        return self._isSubtree(t1Root.leftChild,t2Root) or self._isSubtree(t1Root.rightChild,t2Root)
        
    def _isSubtree(self,node1, node2):
        if node1 == None:
            return False
        
        if node1.value == node2.value:
            if self._isSameTree(node1.leftChild,node2.leftChild) and self._isSameTree(node1.rightChild,node2.rightChild):
                return True
            
        self._isSubtree(node1.leftChild, node2) or self._isSubtree(node1.rightChild, node2)
        
    def _isSameTree(self,node1,node2):
        if node1 == None and node2 == None:
            return True
        elif node1 == None and not node2 == None:
            return  False
        elif node2 == None and not node1 == None:
            return True
        
        if node1.value == node2.value:
            return self._isSameTree(node1.leftChild, node2.leftChild) and self._isSameTree(node1.rightChild, node2.rightChild)
        else:
            return False
        
    '''
    Problem statement 4.8
    '''
    pathList = []
    def printAllPaths(self,bst,val):
        nodeList = None
        nodeList[0:] = bst.getAllNodes()

        for n in nodeList:
            l = []
            currNodeValue = n.value
            if currNodeValue == val:
                l[0] = n
                self.pathList.append(l)
                break
            elif currNodeValue < val:
                l1 = []
                l2 = []
                l1[0] = n
                l2[0] = n
                if not self._getPath(n.leftChild,val-currNodeValue) == None:
                    l1[1:] = self._getPath(n.leftChild,val-currNodeValue)
                    self.pathList.append(l1)
                
                if not self._getPath(n.rightChild,val-currNodeValue) == None:
                    l2[1:] = self._getPath(n.rightChild,val-currNodeValue)
                    self.pathList.append(l2) 
            
                
    def _getPath(self,currentNode,val):
        currNodeValue = currentNode.value
        
        if currNodeValue == val:
            l = []
            ll = []
            l[0] = currentNode
            ll.append(l)
            return ll
        elif currNodeValue < val:
            ll = self._getPath(currentNode.leftChild, val-currNodeValue)
            newll = None
            if not ll == None:
                while l in ll:
                    newll.append(l.insert(0, currNodeValue))
            
            ll = self._getPath(currentNode.rightChild, val-currNodeValue)
            if not ll == None:
                while l in ll:
                    newll.append(l.insert(0, currNodeValue))
            
            return newll
        else:
            return None
            
        
        
            
        
        
        
        
        
                     
            
        
        
        
            
            
        
        
    
    