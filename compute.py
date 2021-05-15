import json, math

import numpy as np
import matplotlib.pyplot as plt
from pysat.solvers import Solver

def generate_box_sizes(maximum):
    for width in range(1, maximum + 1):
        for depth in range(1, width + 1):
            for height in range(1, depth + 1):
                volume = width * height * depth
                if volume % 8 != 0:
                    continue
                yield width, height, depth

def as_tuple(arr):
    arr = arr.tolist()
    return tuple(tuple(row) for row in arr)

def gen_rotations():
    # Not super clever, but it works
    identity = np.identity(3).astype(int)

    rotate_x = np.array([
        [ 0, -1,  0],
        [ 1,  0,  0],
        [ 0,  0,  1],
    ])
    rotate_y = np.array([
        [ 0,  0, -1],
        [ 0,  1,  0],
        [ 1,  0,  0],
    ])
    rotate_z = np.array([
        [ 1,  0,  0],
        [ 0,  0, -1],
        [ 0,  1,  0],
    ])
    prev_rotation_count = 0
    rotations = {as_tuple(identity)}
    while prev_rotation_count != len(rotations):
        prev_rotation_count = len(rotations)

        prev_rotations = [np.array(rotation) for rotation in rotations]
        for transform in (rotate_x, rotate_y, rotate_z):
            for rotation in prev_rotations:
                rotations.add(as_tuple(transform @ rotation))

    return [np.array(rotation) for rotation in rotations]


def best_aspect(N):
    for i in reversed(range(1, math.floor(math.sqrt(N)) + 1)):
        if N % i == 0:
            return (i, N // i)
    else:
        assert False

def show_versions(versions):
    fig = plt.figure()

    width, height = best_aspect(len(versions))

    for i, version in enumerate(versions):
        size = np.max(version, 0) + 1
        
        volume = np.zeros(size, bool)
        for coord in version:
            volume[tuple(coord)[::-1]] = True
        
        ax = fig.add_subplot(width, height, i + 1, projection='3d')
        ax.voxels(volume)
    plt.show()

def create_variable_generator(width, height, depth, variables_per_cell):
    def generate(x, y, z, i):
        if i < 0 or i >= variables_per_cell:
            assert False
        x = x % width
        y = y % height
        z = z % depth

        return 1 + i + variables_per_cell*(x + width * (y + height * z))
    return generate

def no_two_set(variables):
    clauses = []
    for i, var_a in enumerate(variables):
        for var_b in variables[:i]:
            clauses.append([-var_a, -var_b])
    return clauses

def implies(condition, consequences):
    inverse_condition = [-var for var in condition]
    return [inverse_condition + consequence for consequence in consequences]

def iterate_cells(width, height, depth):
    for x in range(width):
        for y in range(height):
            for z in range(depth):
                yield x, y, z


def interpret_solution(width, height, depth, block_count, solution):
    variables_per_cell = block_count*2 + 8
    variables = [False] * (width * height * depth * variables_per_cell)
    for item in solution:
        variables[abs(item) - 1] = item > 0

    variables = np.array(variables).reshape((depth, height, width, variables_per_cell))

    blocks = []
    for x, y, z in iterate_cells(width, height, depth):
        for i in range(block_count):
            if variables[z, y, x, i]:
                blocks.append({'position': [x, y, z], 'orientation': i})
    return blocks

def get_shapes():
    with open('unfolding.json') as f:
        data = json.load(f)
    data = data['unfoldings']
    shapes = [np.array(shape['coords']) for shape in data]

    return shapes

def get_rotations_of_shape(rotations, shape):
    versions = set()
    for rotation in rotations:
        transformed = (rotation @ shape.T).T
        transformed -= np.min(transformed, 0)
        versions.add(frozenset(tuple(vertex.tolist()) for vertex in transformed))

    versions = np.array([tuple(version) for version in versions])
    return versions

def filter_fitting_shapes(shapes, box_size):
    return [shape.tolist() for shape in shapes if np.all(np.max(shape, 0) < box_size)]

if __name__ == '__main__':
    shapes = get_shapes()


    net_size = len(shapes[0])

    rotations = gen_rotations()

    solutions = []

    for shape in shapes:
        versions = get_rotations_of_shape(rotations, shape)
        #show_versions(versions)

        for box_size in [(4,4,4)]:#generate_box_sizes(10):
            print('Trying size:', box_size)
            fitting = filter_fitting_shapes(versions, box_size)
            if len(fitting) == 0:
                continue


            variables_per_cell = len(fitting) * 2 + net_size
            get_variable = create_variable_generator(*box_size, variables_per_cell)
            clauses = []

            # No cell is occupied more than once
            for x, y, z in iterate_cells(*box_size):
                start_variable = get_variable(x, y, z, len(fitting))
                clauses += no_two_set(range(start_variable, start_variable+len(fitting)))

                start_variable = get_variable(x, y, z, len(fitting)*2)
                clauses += no_two_set(range(start_variable, start_variable+net_size))

            # Every cell is occupied
            for x, y, z in iterate_cells(*box_size):
                type_variable = get_variable(x, y, z, len(fitting))
                index_variable = get_variable(x, y, z, len(fitting)*2)
                clauses.append(list(range(type_variable, type_variable + len(fitting))))
                clauses.append(list(range(index_variable, index_variable + net_size)))

            # Cells are grouped into blocks
            for x, y, z in iterate_cells(*box_size):
                for i, version in enumerate(fitting):
                    base_variable = get_variable(x, y, z, i)
                    assert len(version) == net_size
                    for j, (dx, dy, dz) in enumerate(version):
                        type_variable = get_variable(x + dx, y + dy, z + dz, len(fitting) + i)
                        index_variable = get_variable(x + dx, y + dy, z + dz, len(fitting)*2 + j)
                        clauses += implies([base_variable], [[type_variable], [index_variable]])
                        clauses += implies([type_variable, index_variable], [[base_variable]])


            # Cell at (0,0,0) starts a block (not necessary to generate solutions, but may speed it up)
            base_variable = get_variable(0, 0, 0, 0)
            clauses.append(list(range(base_variable, base_variable + len(fitting))))

            with Solver(name='g3', bootstrap_with=clauses) as s:
                if s.solve():
                    solution = interpret_solution(*box_size, len(fitting), s.get_model())
                    print('Found solution', box_size, len(solution))
                    solutions.append({'size': box_size, 'blocks': solution})
                    break
        else:
            print('No solution found')
            solutions.append(None)
        
        with open('solutions.json', 'w') as f:
            json.dump(solutions, f)

