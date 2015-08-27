'''
Created on Dec 24, 2014
Algrothim:
1. first start with enqueuing each element in stack2
2. if dequeue method is called then transfer all the elements from stack2 to stack1, return stack1.pop()
3. if dequeue method is called again, simply return stack1.pop()
    if enqueue method is called then transfer all the elements from stack1 to stack2, finally do stack2.push(element)
4.repeat these steps     

@author: dsingh
'''
from StacksAndQueues.stackClass import Stack

class queueUsingStacks(object):
    '''
    classdocs
    '''


    def __init__(self, params):
        '''
        Constructor
        '''
        self.stack1 = Stack()
        self.stack2 = Stack()
        
    def enqueue(self,element):
        stack1 = self.stack1
        stack2 = self.stack2
        if stack2.isEmpty():
            if stack1.isEmpty():
                #both stacks are Empty
                stack2.push(element)
            else:
                sl = stack1.getLength()
                for i in range(sl):
                    stack2.push(stack1.pop())
                stack2.push(element)
        else:
            #last operation was enqueue
            stack2.push(element)
            
            
    def dequeue(self):
        stack1 = self.stack1
        stack2 = self.stack2
        
        if not stack1.isEmpty():
            #last operation was dequeue
            return stack1.pop()
        else:
            if not stack2.isEmpty():
                sl = stack2.getLength()
                for i in range(sl):
                    stack1.push(stack2.pop())
                return stack1.pop()
            else:
                #both stacks are Empty
                print('Error: please enqueue the list before dequeuing it!')
                return
            