'''
Created on Dec 21, 2015

@author: daman
'''
'''
This application prompts the user for a non existant file name.then has the user 
enter each line of that file(one at a time).Finally, it writes the entire text file to 
disk.
'''

import os
ls = os.linesep

#get file name
while True:
    fname = input('enter file name')
    if os.path.exists(fname):
        print("Error: '%s' already exists", fname)
    else:
        break

#get file content 
all = []
print("\n Enter lines('.' to quit) \n")

#loop until user terminates the input
while True:
    entry = input('> ')
    if entry == '.':
        break
    else:
        all.append(entry)

print("\n",all)        
        
#finally write lines to file with proper line-ending
fobj = open(fname, 'w')
fobj.writelines(['%s%s' % (x, ls) for x in all])
fobj.close()
print("Done!")