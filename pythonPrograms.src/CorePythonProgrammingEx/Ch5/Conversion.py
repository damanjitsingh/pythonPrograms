'''
Created on Dec 25, 2015

@author: damanjits
'''
'''
this function will take time period measured in hours and minutes and return total time in minutes.
e.g. the input shoud be given as: 3 hrs 47 min
'''
def timeInMinutes(time):
    l = time.split(' ')
    return int(l[0])*60 + int(l[2])

if __name__ == '__main__':
    result = timeInMinutes(input("Enter time. You can enter like 3 hrs 45 min"))
    print("Time in minutes is ",result)
    