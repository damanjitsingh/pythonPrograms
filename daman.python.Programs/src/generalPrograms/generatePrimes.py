'''
Created on Jan 13, 2015

@author: dsingh
'''
'''
this function will generate all the prime numbers till n
'''

def generatePrimes(n):
    primes = []
    primes .append(1)
    
    for i in range(2,n):
        isPrime = True
        for j in range(2,i-1):
            if i%j == 0:
                isPrime = False
                break
        if isPrime:
            primes.append(i)
            
    print(primes)

if __name__ == '__main__':
    #print timer.start()
    generatePrimes(151)
            
        