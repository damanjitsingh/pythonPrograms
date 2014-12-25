'''
Created on Dec 23, 2014

@author: dsingh
'''
from StacksAndQueues.stackClass import Stack
from StacksAndQueues.SetofStacks import stackSet

def test_stackClass():
    x = Stack()
    x.peek()
    x.push(2)
    x.push(1)
    x.peek()
    x.push(3)
    print('Min is ',x.min())
    print('First poped element is ', x.pop())

def test_SetofStacks():
    x = stackSet()
    x.push(2)
    x.push(1)
    x.push(3)
    x.push(12)
    x.push(10)
    x.push(22)
    x.pop()
    x.pop()
    x.pop()
    x.pop()
    
#call the functions that needs to be tested
test_stackClass()
#test_SetofStacks()
