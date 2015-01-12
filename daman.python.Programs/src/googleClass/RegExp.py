'''
Created on Jan 11, 2015

@author: dsingh
'''
import re

def Find(pat, text):
    match = re.search(pat, text)
    if match:
        print 'found' , match.group()
    else:
        print 'not found'
        
def findAll(pat, text):
    match  = re.findall(pat, text)
    if match:
        print 'found' , match
    else:
        print 'not found'

def main():
    #r is for raw string in python, any back slash present in the string does not has special meaning 
    Find(r'iiig', 'called piiig')
    #\w matched word character, any char, digit, underscore
    Find(r':\w\w\w', 'blah :c1t blah blah ')
    #/d matches any digit
    Find(r'\d\d\d', 'blah :123 blah blah ')
    #/s matches single space
    Find(r'\d\s\d\s\d','blah :1 2 3 blah')
    # + means one or more spaces in the below example, * means zero or more
    Find(r'\d\s+\d\s+\d','blah :1      2      3 blah')
    #space is not a word character
    Find(r':\w+','blah :kitten some number of word characters')
    #/S matches all non white space characters
    Find(r':\S+', 'blah :kitten123123@&yatta blah blah')
    #extracting email from the text below
    Find(r'\S+@\S+', 'blah d.singh@gmail.com yatta #@ blah blah')
    #[] brackets matched set of characters, '.' here means actual dot charachter
    Find(r'[\w.]+@[\w.]+', 'blah d.singh@gmail.com yatta #@ blah blah')
    #to separate user name and host name, () parenthesis are used to extract the part you want to extract
    m = re.search(r'([\w.]+)@([\w.]+)', 'blah d.singh@gmail.com yatta #@ blah blah')
    print m.group(1), m.group(2)
    
    #find all the matches of the pattern, matching does not stopped after finding the first pattern
    findAll(r'[\w.]+@[\w.]+', 'blah d.singh@gmail.com yatta foo@bar')
    
    
if __name__ == '__main__':
    main()
    