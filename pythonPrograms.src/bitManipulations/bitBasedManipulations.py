'''
this function will convert the decimal number to binary
'''
def bin(s):
    return str(s) if s<=1 else bin(s>>1) + str(s&1)

def binMyWay(n):
    if n<=1:
        return str(n)
    else:
        return str(n&1) + binMyWay(n>>1)
        

#print binMyWay(23)

'''
You are given two 32-bit numbers, N and M, and two bit positions, i and j. Write a
method to set all bits between i and j in N equal to M (e.g., M becomes a substring of
N located at i and starting at j).
EXAMPLE:
Input: N = 10000000000, M = 10101, i = 2, j = 6
Output: N = 10001010100
'''
def setBits(n,m,i,j):
    print 'value of n is ' + bin(n) + ' value of m is ' + bin(m) + '\n' 
    m = m<<(i)
    a=1
    a = a<<(j+1)
    b = pow(2, i)-1
    c = a|b#this no. has all 0,s between i and jth position inclusive, all other bits are 1
    n = n&c
    n=n|m
    print 'result = ' + bin(n)

def decimalToBin(s):
    beforeDecimal,afterdecimal = s.partition('.')
    if beforeDecimal.equal('') | afterdecimal.equal('') == "":
        print 'invalid input '
    print beforeDecimal + ' '+ afterdecimal
    adb = fractionToBin(afterdecimal)
    bdb = bin(beforeDecimal)
    return bdb + '.' + adb
    
# input is a string representing the fractional part of a number, e.g for 3.35, f is 35 in string    
def fractionToBin(f):
    n = int(f)
    dec = n//(pow(10,len(f)))
    s=''
    while not dec == 1.0:
        dec = dec*2
        b,a = str(dec).partition('.')
        s = s + b
        dec = float(a)
    return s[::-1]

'''
problem 5.3
def nextHigher(n):
    #if the first digit is 1 
    if n&1 == 1:
        #look for first 0
        firstZero = 1
        m = n
        while not m == 0:
            m = m>>1
            if not (m&1) == 0:
                firstZero+=1
            else:
                break
        #swap the firstZeroth bit with firstZerotth-1 bit
        
    else:
        #look for first 1 and apply rule 1 and 2
        #rule 1: xxx010 to xxx100
        #rule 2: 011110 to 111110  need to check!!!
'''
        

'''
problem 5.5
this problem indirectly asks to calculate number of different bits in two numbers
'''
def diffbits(n1,n2):
    #step1 do xor of n1 and n2
    #step2 count number of 1's in the resulting number
    x = n1^n2
    count=0
    while x:
        if (x&1) == 1:
            count+=1
        x = x>>1
    print bin(n1) + ' has ' + str(count) + ' different bits than ' + bin(n2)

'''
problem 5.6
'''    
def bitSwapping(n):
    n1 = (n<<1)&0xAAAAAAAA
    n2 = (n>>1)&0x66666666
    print 'number ' + bin(n) + 'after swapping gives ' + bin(n1|n2)
    
    
    