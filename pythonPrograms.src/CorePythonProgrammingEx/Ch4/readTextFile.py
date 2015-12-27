'''
Created on Dec 21, 2015

@author: daman
'''
fname = input('Enter file name')

try:
    fobj = open(fname, 'r')
except IOError as e:
    print('file open error',e)
else:
    for line in fobj:
        print(line)
    fobj.close()
    