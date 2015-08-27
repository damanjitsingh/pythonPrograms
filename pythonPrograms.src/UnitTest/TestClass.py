'''
Created on Mar 22, 2015

@author: daman
'''

import unittest
from Multiply import multiply

class TestUM(unittest.TestCase):

    def setUp(self):
        pass

    def test_numbers_3_4(self):
        self.assertEqual(multiply(4,3), 12)

    def test_strings_a_3(self):
        self.assertEqual(multiply('a',3), 'aaa')

if __name__ == '__main__':
    unittest.main()
        