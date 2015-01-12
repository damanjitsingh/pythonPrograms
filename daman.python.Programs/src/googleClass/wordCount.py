'''
Created on Jan 7, 2015

@author: dsingh
'''

def wordCount(fileName):
    wordList = {}
    l = []
    try:
        f = open(fileName, 'r')
    except IOError as e:
        print e.strerror
            
    for line in f:
        words = line.split()
        for word in words:
            if wordList.get(word) == None:
                wordList[word] = 1
            else:
                wordList[word] += 1
    f.close()
    print sorted(wordList.items())
    
def main():
    wordCount(r'C:\Daman\PythonStuff\google-python-exercises\basic\alice.txt')
    
if __name__ == '__main__':
    main()
        
    
