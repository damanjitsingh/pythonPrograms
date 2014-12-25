'''
Created on Dec 24, 2014

@author: dsingh
'''

from stackClass import Stack

class stackSet():
    '''
    classdocs
    '''
    THRESHOLD = 4

    def __init__(self):
        '''
        Constructor
        '''
        self.stackSet = []
        singleStack = Stack()
        self.stackSet.append(singleStack)
        
    def push(self, element):
        #get the top most stack
        topstack = self.stackSet.pop()
        if topstack.getLength() < self.THRESHOLD:
            topstack.push(element)
            self.stackSet.append(topstack)
        else:
            #create a new stack
            self.stackSet.append(topstack)
            newStack = Stack()
            newStack.push(element)
            self.stackSet.append(newStack)
        print('length of stack set is ',len(self.stackSet))
            
    def pop(self):
        topStack = self.stackSet.pop()
        
        if topStack.isEmpty():
            print('push some element before popping!!')
            return
        
        element = topStack.pop()
        
        if not topStack.isEmpty():
            self.stackSet.append(topStack)
        
        print('length of stack set is ',len(self.stackSet))    
        return element
                
            
            
            
            
     
        