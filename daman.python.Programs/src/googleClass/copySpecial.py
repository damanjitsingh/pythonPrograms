'''
Created on Jan 12, 2015

@author: dsingh
'''
import os
from os.path import join
from os import listdir 
import re
import shutil

destDir = r'C:\Daman\PythonStuff\google-python-exercises\copyspecial\dest'

def listSpecial(dirName):
    fileNames = listdir(dirName)
    
    for fileName in fileNames:
        #select special fileName
        match = re.search(r'__\w+__[\w.]+',fileName)
        if match:
            #copy the absolute path in a list
            fpath = join(dirName,fileName)
            print os.path.abspath(fpath)
            #now copy each file to the destination path
            if not os.path.exists(destDir):
                #create the dir
                os.makedirs(destDir)
            shutil.copy(fpath, destDir)
    
    
def main():
    listSpecial(r'C:\Daman\PythonStuff\google-python-exercises\copyspecial')
    
if __name__ == '__main__':
    main()