# Enter your code here. Read input from STDIN. Print output to STDOUT
'''
Created on Feb 4, 2015

@author: daman
'''

'''
Problem Statement

Now we will see how to implement a nested list. There is a classroom of 'n' students and you are given their names and marks in physics. Store them in a nested list and print the name of each student who got the second lowest marks in physics.

NOTE: If there are more than one student getting same marks, make sure you print the names of all students in alphabetical order, in different lines.

Input Format

Integer N followed by alternating sequence of N strings and N numbers.

Output Format

Name of student

Sample Input

5
Harry
37.21
Berry
37.21
Tina
37.2
Akriti
41
Harsh
39

Sample Output
Berry
Harry
'''

import sys

def sortNumbers(n,l):
    if l == None:
        print 'Invalid input'
        
    #from the list create the Dictionary
    ns = []
    listend = 2*n-1
    
    for i in range(0,listend,2):
        ns.append([l[i],float(l[i+1])])
        
    #now sort nested list(ns) for values
    nss = sorted(ns,key = lambda element:element[1])
    
    isSLFound = False
    rns = []
    #finding the second lowest score
    for i in range(1,len(nss)):
        previousTuple = nss[i-1]
        currentTuple = nss[i]
        
        if previousTuple[1] == currentTuple[1] and not isSLFound:
            # simply iterate forward
            continue
        elif previousTuple[1] == currentTuple[1] and isSLFound:
            #store all second lowest in one nested list
            rns.append(currentTuple)
        elif not previousTuple[1] == currentTuple[1] and not isSLFound:
            #current tuple is second lowest
            isSLFound = True
            rns.append(currentTuple)
        elif not previousTuple[1] == currentTuple[1] and isSLFound:
            break
            
    if len(rns) >1:
        #print(sorted(rns,key = lambda element:element[0]))
        rns = sorted(rns,key = lambda element:element[0])
        
    for l in rns:
        sys.stdout.write(l[0])
        

def main():
    #sortNumbers(sys.argv[1], sys.argv[2:])
    data = sys.stdin.readlines()
    sortNumbers(int(data[0]), data[1:])
    
if __name__ == '__main__':
    #sortNumbers(5, ['Harry',37.21,'Berry',37.21,'Tina',37.2,'Akriti',41,'Harsh',39])
    #code for parsing input from stdin
    main()