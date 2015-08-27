for f in range(input()):
    x = input();k=10;t=1
    while k>1:k-=1;t=1+t*1j*x/k
    print'%.3f\n'*2%(t.imag,t.real)