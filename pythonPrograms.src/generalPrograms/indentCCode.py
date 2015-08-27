'''
Created on Aug 25, 2015

@author: damanjits
'''

'''
This function will parse each line of .c file and remove '\t''s in front of line with required space chars
e.g 
\tint err = 0;
will be
    int err = 0;
    
The take away from this implementation is that python add extra'\' to the strings already containing '\' to avoid it being treated
as backslash char.More info at 
http://stackoverflow.com/questions/32229321/python-prepends-character-to-the-start-of-strings-which-starts-with-char?noredirect=1#comment52341206_32229321
'''
def indentCCode(srcFile,destFile):
    dfp = open(destFile,'w')
    result = ''
    with open(srcFile) as fp:
        for line in fp:
            lineLen = len(line)
            count = 0
            while count<lineLen:
                if line[count]=='\\' and line[count+1]=='t':
                    result = result+'    '
                    count = count+2
                else:
                    break
            result = result+line[count:]
            print(result)
            dfp.write(result)
            result = ''
        dfp.close()
               
    return

'''
This short program uses regular expressions
'''
import re
def indentCCodeRegEx(srcFile,destFile):
    dfp = open(destFile,'w')
    with open(srcFile) as fp:
        for line in fp:
            newLine = re.sub('\t','    ',line)
            dfp.write(newLine)
        dfp.close()

if __name__ == '__main__':
    indentCCode(r'/Users/damanjits/Notebooks/tabs.txt',r'/Users/damanjits/Notebooks/newTabs.txt')
    indentCCode(r'/Users/damanjits/Notebooks/tabs.txt',r'/Users/damanjits/Notebooks/newRETabs.txt')
