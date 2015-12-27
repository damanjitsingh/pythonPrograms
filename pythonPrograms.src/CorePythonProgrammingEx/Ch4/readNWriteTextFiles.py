'''
Created on Dec 23, 2015

@author: damanjits

This application combines the functionality of makeTextFile and readTextFile
Also it has the feature of editing a text file
'''
import os
from tkinter.filedialog import askopenfile, asksaveasfile
from tkinter.messagebox import showerror
ls = os.linesep

def makeTextFile():
    #get file name
    while True:
        fname = input('enter file name for writing text to')
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
    
    #finally write lines to file with proper line-ending
    fobj = open(fname, 'w')
    fobj.writelines(['%s%s' % (x, ls) for x in all])
    fobj.close()
    print("Done!")
    
    
def readTextFile():
    fname = input('Enter file name')
    try:
        fobj = open(fname, 'r')
    except IOError as e:
        print('file open error',e)
    else:
        for line in fobj:
            print(line)
        fobj.close()

'''
This is the utility function which allows user to edit a file with following features:
User can edit an existing text file and save the changes.
User can discard the changes, the file will be retained in its original form.
If program ended abnormally original file will be restored.
'''
from tkinter import *
filename = None

def editTextFile():
    fname = input('enter file name for writing text to')
    
    def newFile():
        global filename
        filename = "Untitled"
        text.delete(0.0,END)
        
    def saveFile():
        t = text.get(0.0,END)
        f = open(fname,'w')
        f.write(t)
        f.close()
    
    def saveAs():
        f = asksaveasfile(mode='w',defaultextension='.txt')
        t = text.get(0.0,END)
        try:
            f.write(t.rstrip())
        except:
            showerror(title="Error",message="File save fail...")
            
    def openFile():
        f = askopenfile(mode='r')
        t=f.read()
        text.delete(0.0,END)
        text.insert(0.0,t)
    
    #start implementation here
    root = Tk()
    root.title("My Python text file editor")
    root.minsize(width=400, height=400)
    root.maxsize(width=400, height=400)

    text = Text(root,width=400,height=400)
    text.pack()
    
    #creating menu bar options
    menubar = Menu(root)
    filemenu = Menu(menubar)
    filemenu.add_command(label="New",command=newFile)
    filemenu.add_command(label="Open",command=openFile)
    filemenu.add_command(label="Save",command=saveFile)
    filemenu.add_command(label="Save As...",command=saveAs)

    filemenu.add_separator()
    filemenu.add_command(label="Quit",command=root.quit)
    menubar.add_cascade(label='File',menu=filemenu)
    
    root.config(menu=menubar)
    root.mainloop()
        
if __name__ == '__main__':
    rw = int(input("Enter 1 for read,0 for write mode and 2 for edit"))
    if(rw == 0):
        print("Entering write mode \n")
        makeTextFile()
    elif(rw == 1):
        print("Entering read mode \n")
        readTextFile()
    else:
        print("Entering editing mode \n")
        editTextFile()
        
    
