'''
Created on Dec 23, 2014

@author: dsingh
'''

class Stack():
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.stack = []
        print(len(self.stack))
        
    def push(self,element):
        self.stack.append(element)
    
    #this push function will maintain the stack in ascending order
    def pushAscending(self,element):
        stack = self.stack
        if self.isEmpty():
            stack.append(element)
        else:
            current = self.peek()
            if current <= element:
                stack.append(element)
            else:
                stack.insert(len(stack)-1, element)
                
        
    def pop(self):
        return self.stack.pop()
    
    def min(self):
        self.scopy = self.stack.copy()
        self.scopy.sort()
        return self.scopy[0]
    
    def isEmpty(self):
        if len(self.stack) == 0:
            return True
        else:
            False
            
    def getLength(self):
        return len(self.stack)
    
    #this function returns the value of the last added element(i.e. top of the collection) without removing it form the stack or queue
    def peek(self):
        if not self.isEmpty():
            element = self.stack.pop()
            self.stack.append(element)
            print('last element is ',element)
        else:
            print('stack is empty!')
            
    def sortStackInAscendingOrderVersion1(self):
        if self.isEmpty():
            print('Empty stack!')
            
        stack = self.stack
        length = len(stack)
        
        for i in range(length-1):
            for j in range(i+1,length):
                if stack[j] < stack[i]:
                    temp = stack[i]
                    stack[i] = stack[i+1]
                    stack[i+1] = temp 
        
        return stack
    
    #this function will return new stack object whose elements are sorted in ascending order
    def sortStackInAscendingOrderVersion2(self):
        if self.isEmpty():
            print('Empty stack!')
        
        sortedStack = Stack()
        stack = self.stack    
        lastElement = stack.pop()
        length = len(stack)
        
        sortedStack.push(lastElement)
        for i in range(length):
            element = stack.pop()
            if element < sortedStack.peek():
                currentElement = sortedStack.pop()
                sortedStack.push(element)
                sortedStack.push(currentElement)
            else:
                sortedStack.push(element)
        
        return sortedStack
            
        
        
        