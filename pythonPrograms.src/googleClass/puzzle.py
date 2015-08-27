'''
Created on Jan 12, 2015

@author: dsingh
'''
import sys
import re
import os
from os import path
import urllib
from os.path import *

def getUrls(fileName):
    try:
        f = open(fileName)
    except IOError:
        print 'file open error'
        return
    
    text = f.read()
    match = re.findall(r'GET\s(\S+puzzle\S+)\s', text)
    
    if match:
        urlls = []
        for element in match:
            urlls.append('http://www.corp.google.com' + element)
        print urlls
    else:
        print 'No url is matched'
    
    return urlls
        
def download(urlList,opdir):
    if urlList == None:
        print 'empty url list, exiting!'
        return
    
    if not os.path.exists(opdir):
        #create the dir
        os.makedirs(opdir)
    i = 0
    for myUrl in urlList:
        urllib.urlretrieve(myUrl, join(opdir,'img'+str(i)))
        i+=1
    
    

def main():
    args = sys.argv[1:]
    if not args:
        print "usage: [--todir dir]";
        sys.exit(1)
        
    todir = ''
    if args[0] == '--todir':
        opdir = args[1]
        ipLogFile = args[2]
        download(getUrls(r''+ipLogFile),opdir)
    else:
        #just print the urls
        ipLogFile = args[0]
        getUrls(r''+ipLogFile)
        

if __name__ == '__main__':
    main()