'''
Created on Jan 11, 2015

@author: dsingh
'''
import re
import operator

def findPatterns(fileName):
    fr = open(fileName, 'r')
    fileText = fr.read()
    year = re.search(r'Popularity in \d\d\d\d', fileText).group().split()[2]
    
    writeFileName = fileName[:-5] + '_summary.txt'
    
    try:
        fw = open(writeFileName, 'w')
    except:
        print 'file create error'
        return
    
    fw.write(year + '\n')
    allList = re.findall(r'<tr align="right"><td>(\d+)</td><td>(\w+)</td><td>(\w+)</td>', fileText)
    #allList will contains tuples of 1,name,name
    myDict = {}
    for tup in allList:
        rank = tup[0]
        maleName = tup[1]
        femaleName = tup[2]
        
        if myDict.get(maleName):##store the name with high popularity
            if myDict[maleName] > rank:
                myDict[maleName] = rank
        elif myDict.get(femaleName):
            if myDict[femaleName] > rank:
                myDict[femaleName] = rank
        else:
            myDict[maleName] = rank
            myDict[femaleName] = rank
            
    #Now I need to sort the dict
    sortTuple = sorted(myDict.items(), key=operator.itemgetter(0))
    #finally write tuples to file
    fw.write('\n'.join('%s %s' % t for t in sortTuple))

from os import listdir
from os.path import isfile, join

def iterateAllFiles(dirName):
    #get all the files that are of html ext. under given directory
    onlyHTMLFiles = []
    for f in listdir(dirName):
        fullPath = join(dirName,f)
        if isfile(fullPath) and fullPath[-4:] == 'html':
            onlyHTMLFiles.append(fullPath)
    
    for pthName in onlyHTMLFiles:
        print 'reading file :',pthName
        findPatterns(pthName)
    
if __name__ == '__main__':
    #findPatterns(r'C:\Daman\PythonStuff\google-python-exercises\babynames\baby1990.html')
    iterateAllFiles(r'C:\Daman\PythonStuff\google-python-exercises\babynames')
    
    
        
        
        