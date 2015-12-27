'''
Created on Dec 25, 2015

@author: damanjits
'''

#given num1 and num2 as strings compute the product and return the result.
def product(num1,num2):
    return eval(num1)*eval(num2)

if __name__ == '__main__':
    nums = input("Enter 2 numbers separated by comma")
    num1,num2 = nums.split(sep=',')
    print("Product of ",num1," and ",num2," is ",product(num1, num2)