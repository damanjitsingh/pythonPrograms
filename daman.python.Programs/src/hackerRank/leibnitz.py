import sys

def leib(n):
    num = 0
    i = 0.0
    while i < n:
        num = num + (pow(-1, i)/(2*i+1))
        i+=1.0
        
    print('%.15f' %num)

def main():
    inp = sys.stdin
    
    numbers = int(inp.readline().rstrip())   
    count = 0
    
    fd = []
    while count < numbers:
        fd.append(float(inp.readline().rstrip()))
        count+=1
        
    for n in fd:
        leib(n)
        
        
if __name__ == '__main__':
    #main()
    exec"print'%.15g'%sum((-1.)**i/(i-~i)for i in range(input()));"*input()
    
