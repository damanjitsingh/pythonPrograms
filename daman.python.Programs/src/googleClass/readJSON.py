'''
Created on Jan 9, 2015

@author: dsingh
'''
import json
from pprint import pprint
from operator import itemgetter

def readFile():
    json_data=open(r'C:\Daman\Research\PermissionMapping\organized-series-10-results\40.json')

    data = json.load(json_data)
    pprint(data)
    sortedDataVersion = sorted(data,key = itemgetter('version'))
    pprint(sortedDataVersion)
    
def main():
    print 'i am in main'
    #myfile()

if __name__ == '__main__':
    readFile()