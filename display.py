import json
from typing import overload
import numpy as np

from collections import Counter

import matplotlib.pyplot as plt

from compute import filter_fitting_shapes, gen_rotations, get_rotations_of_shape, get_shapes


def solution_to_grid(solution, shapes):
    box_size = solution['size']
    filled = np.full(box_size[::-1], -1)

    overlaps = 0
    for i, block in enumerate(solution['blocks']):
        shape = np.array(shapes[block['orientation']])
        for coord in shape:
            coord = (coord + block['position']) % box_size

            index = tuple(coord)[::-1]

            overlaps += filled[index] != -1

            filled[index] = i

    return filled, overlaps

if __name__ == '__main__':
    with open('solutions.json') as f:
        solutions = json.load(f)
    shapes = get_shapes()

    print('Total evaluated:', len(solutions))

    solutions = [(solution, shape, i) for i, (solution, shape) in enumerate(zip(solutions, shapes)) if solution is not None]

    print('Total solved:', len(solutions))


    lengths = np.array([len(item['blocks']) for item, _, _ in solutions])
    print(Counter(lengths))

    sizes = [tuple(item['size']) for item, _, _ in solutions]
    print(Counter(sizes))

    for item, _, _ in solutions:
        size = item['size']

        volume_a = size[0] * size[1] * size[2]
        volume_b = 8 * len(item['blocks'])
        if volume_a != volume_b:
            print('Invalid', volume_a, volume_b)

    
    rotations = gen_rotations()
    
    for solution, shape, i in solutions:
        versions = filter_fitting_shapes(get_rotations_of_shape(rotations, shape), solution['size'])

        filled, overlaps = solution_to_grid(solution, versions)


        print(i, overlaps, np.all(filled != -1))
        

        colour_map = np.random.random((len(solution['blocks']), 3))

        colours = colour_map[filled, :]

        id = i + 1
        
        for i in range(len(solution['blocks'])):
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            ax.voxels(filled <= i, facecolors=colours)
            fig.savefig(f'images/{id}_{i}.png')