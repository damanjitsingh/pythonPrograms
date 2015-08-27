'''
Created on Jun 26, 2015

@author: damanjits
'''
import functools
from random import random

'''
https://codewords.recurse.com/issues/one/an-introduction-to-functional-programming
'''

def mapReduceFilter():
    people = [{'name': 'Mary', 'height': 160},
             {'name': 'Isla', 'height': 80},
             {'name': 'Sam'}]
     
    peopleWithHeight = list(filter(lambda x:'height' in x,people))
    heightTotal = functools.reduce(lambda a,x:a+x['height'],
                         peopleWithHeight,
                         0)
    print(heightTotal,heightTotal/len(peopleWithHeight))
    
    
'''
imperative version of car race program
'''
def carRaceNonFuncImperative():
    time = 5
    car_positions = [1, 1, 1]
    
    while time:
        # decrease time
        time -= 1
    
        print('')
        for i in range(len(car_positions)):
            # move car
            if random() > 0.3:
                car_positions[i] += 1
    
            # draw car
            print('-' * car_positions[i])
    
    

'''
declarative version of car race program
'''
def carRaceNonFuncDeclarative():

    def move_cars():
        for i, _ in enumerate(car_positions):
            if random() > 0.3:
                car_positions[i] += 1
    
    def draw_car(car_position):
        print('-' * car_position)
    
    def run_step_of_race():
        global time
        time -= 1
        move_cars()
    
    def draw():
        print('')
        for car_position in car_positions:
            draw_car(car_position)
    
    time = 5
    car_positions = [1, 1, 1]
    
    while time:
        run_step_of_race()
        draw()

'''
functional version of car race program
'''
def carRaceFunctional():

    def move_cars(car_positions):
        return map(lambda x: x + 1 if random() > 0.3 else x,
                   car_positions)
    
    def output_car(car_position):
        return '-' * car_position
    
    def run_step_of_race(state):
        return {'time': state['time'] - 1,
                'car_positions': move_cars(state['car_positions'])}
    
    def draw(state):
        print('')
        print('\n'.join(map(output_car, state['car_positions'])))
    
    def race(state):
        draw(state)
        if state['time']:
            race(run_step_of_race(state))
    
    race({'time': 5,
          'car_positions': [1, 1, 1]})
    
    
'''
Use of pipe lines
'''
'''Initial imperative code'''
bands = [{'name': 'sunset rubdown', 'country': 'UK', 'active': False},
         {'name': 'women', 'country': 'Germany', 'active': False},
         {'name': 'a silver mt. zion', 'country': 'Spain', 'active': True}]

def wihoutPipelines():

    def format_bands(bands):
        for band in bands:
            band['country'] = 'Canada'
            band['name'] = band['name'].replace('.', '')
            band['name'] = band['name'].title()
    
    format_bands(bands)
    print(bands)
    
'''
with pipelines
'''
def withPipelines():
    def pipeline_each(data, fns):
        return functools.reduce(lambda a, x: map(x, a),
                      fns,
                      data)
        
    def assoc(_d, key, value):
        from copy import deepcopy
        d = deepcopy(_d)
        d[key] = value
        return d

    def call(fn, key):
        def apply_fn(record):
            return assoc(record, key, fn(record.get(key)))
        return apply_fn
        
        
    print(pipeline_each(bands, [call(lambda x: 'Canada', 'country'),
                            call(lambda x: x.replace('.', ''), 'name'),
                            call(str.title, 'name')]))


tuple([1,2,3,4])

if __name__ == '__main__':
    mapReduceFilter()
    
