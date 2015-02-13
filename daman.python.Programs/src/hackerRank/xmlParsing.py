# Enter your code here. Read input from STDIN. Print output to STDOUT
'''
Created on Feb 7, 2015

@author: daman
'''

import xml.etree.ElementTree as etree
import sys

def parse(xml):
    try:
        elem = etree.fromstring(''.join(xml))
    except:
        print 0
        return
    
    tree = etree.ElementTree(elem)
    iter  = tree.getiterator()
    
    totalAttribCount = 0
    for child in iter:
        currentAttr = child.attrib
        totalAttribCount = totalAttribCount + len(currentAttr)
        
    print totalAttribCount
    
        
def maxDepth(xml):
    try:
        elem = etree.fromstring(xml)
    except:
        print 0
        return
    
    tree = etree.ElementTree(elem)
    
    root = tree.getroot()
   
    maximumDepth = 0 
    for child in root:
        currentDepth = 1 + __recursiveDepth(child)
        if currentDepth > maximumDepth:
            maximumDepth = currentDepth
            
    print maximumDepth
        
def __recursiveDepth(element):
    maximumDepth = 0
    
    for child in element:
        currentDepth = 1 + __recursiveDepth(child)
        if currentDepth > maximumDepth:
            maximumDepth = currentDepth
            
    return maximumDepth
    
    
def main():
    inp = sys.stdin
    
    nlines = int(inp.readline())   
    count = 0
    
    xmlString = ''
    while count < nlines:
        xmlString = xmlString+inp.readline()
        #xmlLines.append(inp.readline())
        count+=1
    
    #parse(xmlLines)
    maxDepth(xmlString)

if __name__ == '__main__':
    main()