import numpy as np
import pytest

import psyneulink.core.components.functions.statefulfunctions.memoryfunctions as Functions
import psyneulink.core.llvm as pnlvm

np.random.seed(0)
SIZE=10
test_var = np.random.rand(2, SIZE)
test_initializer = np.array([[test_var[0], test_var[1]]])
test_noise_arr = np.random.rand(SIZE)

RAND1 = np.random.random(1)
RAND2 = np.random.random()

test_data = [
# Default initializer does not work
#    (Functions.Buffer, test_var, {'rate':RAND1}, [[0.0],[0.0]]),
    (Functions.Buffer, test_var[0], {'history':512, 'rate':RAND1, 'initializer':[test_var[0]]}, [[0.03841128, 0.05005587, 0.04218721, 0.0381362 , 0.02965146, 0.04520592, 0.03062659, 0.0624149 , 0.06744644, 0.02683695],[0.14519169, 0.18920736, 0.15946443, 0.1441519 , 0.11208025, 0.17087491, 0.11576615, 0.23592355, 0.25494239, 0.10144161]]),
    (Functions.ContentAddressableMemory, test_var, {'rate':RAND1}, [[
       0.5488135039273248, 0.7151893663724195, 0.6027633760716439, 0.5448831829968969, 0.4236547993389047, 0.6458941130666561, 0.4375872112626925, 0.8917730007820798, 0.9636627605010293, 0.3834415188257777], [
       0.7917250380826646, 0.5288949197529045, 0.5680445610939323, 0.925596638292661, 0.07103605819788694, 0.08712929970154071, 0.02021839744032572, 0.832619845547938, 0.7781567509498505, 0.8700121482468192 ]]),
    (Functions.ContentAddressableMemory, test_var, {'rate':RAND1, 'retrieval_prob':0.5},
       [[ 0. for i in range(SIZE) ],[ 0. for i in range(SIZE) ]]),
    (Functions.ContentAddressableMemory, test_var, {'rate':RAND1, 'storage_prob':0.1},
       [[ 0. for i in range(SIZE) ],[ 0. for i in range(SIZE) ]]),
    (Functions.ContentAddressableMemory, test_var, {'rate':RAND1, 'retrieval_prob':0.9, 'storage_prob':0.9}, [[
       0.5488135039273248, 0.7151893663724195, 0.6027633760716439, 0.5448831829968969, 0.4236547993389047, 0.6458941130666561, 0.4375872112626925, 0.8917730007820798, 0.9636627605010293, 0.3834415188257777], [
       0.7917250380826646, 0.5288949197529045, 0.5680445610939323, 0.925596638292661, 0.07103605819788694, 0.08712929970154071, 0.02021839744032572, 0.832619845547938, 0.7781567509498505, 0.8700121482468192 ]]),
    (Functions.ContentAddressableMemory, test_var, {'initializer':test_initializer, 'rate':RAND1}, [[
       0.5488135039273248, 0.7151893663724195, 0.6027633760716439, 0.5448831829968969, 0.4236547993389047, 0.6458941130666561, 0.4375872112626925, 0.8917730007820798, 0.9636627605010293, 0.3834415188257777], [
       0.7917250380826646, 0.5288949197529045, 0.5680445610939323, 0.925596638292661, 0.07103605819788694, 0.08712929970154071, 0.02021839744032572, 0.832619845547938, 0.7781567509498505, 0.8700121482468192 ]]),
# Disable noise tests for now as they trigger failure in ContentAddressableMemory lookup
#    (Functions.ContentAddressableMemory, test_var, {'rate':RAND1, 'noise':RAND2}, [[
#       0.79172504, 0.52889492, 0.56804456, 0.92559664, 0.07103606, 0.0871293 , 0.0202184 , 0.83261985, 0.77815675, 0.87001215 ],[
#       1.3230471933615413, 1.4894230558066361, 1.3769970655058605, 1.3191168724311135, 1.1978884887731214, 1.4201278025008728, 1.2118209006969092, 1.6660066902162964, 1.737896449935246, 1.1576752082599944
#]]),
#    (Functions.ContentAddressableMemory, test_var, {'rate':RAND1, 'noise':[RAND2], 'retrieval_prob':0.5},
#       [[ 0. for i in range(SIZE) ],[ 0. for i in range(SIZE) ]]),
#    (Functions.ContentAddressableMemory, test_var, {'rate':RAND1, 'noise':RAND2, 'storage_prob':0.5},
#       [[ 0. for i in range(SIZE) ],[ 0. for i in range(SIZE) ]]),
#    (Functions.ContentAddressableMemory, test_var, {'initializer':test_initializer, 'rate':RAND1, 'noise':RAND2}, [[
#       0.79172504, 0.52889492, 0.56804456, 0.92559664, 0.07103606, 0.0871293 , 0.0202184 , 0.83261985, 0.77815675, 0.87001215 ],[
#       1.3230471933615413, 1.4894230558066361, 1.3769970655058605, 1.3191168724311135, 1.1978884887731214, 1.4201278025008728, 1.2118209006969092, 1.6660066902162964, 1.737896449935246, 1.1576752082599944
#]]),
]

# use list, naming function produces ugly names
names = [
    "Buffer",
#    "Buffer Initializer",
    "ContentAddressableMemory",
    "ContentAddressableMemory Random Retrieval",
    "ContentAddressableMemory Random Storage",
    "ContentAddressableMemory Random Retrieval-Storage",
    "ContentAddressableMemory Initializer",
#    "ContentAddressableMemory Noise",
#    "ContentAddressableMemory Noise Random Retrieval",
#    "ContentAddressableMemory Noise Random Storage",
#    "ContentAddressableMemory Initializer Noise",
]

GROUP_PREFIX="IntegratorFunction "

@pytest.mark.function
@pytest.mark.memory_function
@pytest.mark.parametrize("func, variable, params, expected", test_data, ids=names)
@pytest.mark.benchmark
def test_basic(func, variable, params, expected, benchmark):
    f = func(default_variable=variable, **params)
    benchmark.group = GROUP_PREFIX + func.componentName;
    f(variable)
    res = f(variable)
    assert np.allclose(res[0], expected[0])
    assert np.allclose(res[1], expected[1])
    benchmark(f, variable)


@pytest.mark.llvm
@pytest.mark.function
@pytest.mark.memory_function
@pytest.mark.parametrize("func, variable, params, expected", test_data, ids=names)
@pytest.mark.benchmark
def test_llvm(func, variable, params, expected, benchmark):
    if func is Functions.Buffer:
        pytest.skip("Not implemented")
    benchmark.group = GROUP_PREFIX + func.componentName;
    f = func(default_variable=variable, **params)
    m = pnlvm.execution.FuncExecution(f)
    m.execute(variable)
    res = m.execute(variable)
    assert np.allclose(res[0], expected[0])
    assert np.allclose(res[1], expected[1])
    benchmark(m.execute, variable)


@pytest.mark.llvm
@pytest.mark.cuda
@pytest.mark.function
@pytest.mark.memory_function
@pytest.mark.parametrize("func, variable, params, expected", test_data, ids=names)
@pytest.mark.benchmark
def test_ptx_cuda(func, variable, params, expected, benchmark):
    if func is Functions.Buffer:
        pytest.skip("Not implemented")
    benchmark.group = GROUP_PREFIX + func.componentName;
    f = func(default_variable=variable, **params)
    m = pnlvm.execution.FuncExecution(f)
    m.cuda_execute(variable)
    res = m.cuda_execute(variable)
    assert np.allclose(res, expected)
    benchmark(m.cuda_execute, variable)

# Test of ContentAddressableMemory without LLVM:
from psyneulink import *

def test_ContentAddressableMemory_with_initializer_and_key_size_same_as_val_size():

    stimuli = {'A': [[1,2,3],[4,5,6]],
               'B': [[8,9,10],[11,12,13]],
               'C': [[1,2,3],[11,12,13]],
               'D': [[1,2,3],[21,22,23]],
               'E': [[9,8,4],[11,12,13]],
               'F': [[10,10,30],[40,50,60]],
               }

    em = EpisodicMemoryMechanism(
            content_size=3,
            assoc_size=3,
            function = ContentAddressableMemory(
                    initializer=np.array([stimuli['F'], stimuli['F']]),
                    duplicate_keys_allowed=True,
                    equidistant_keys_select=RANDOM)
    )

    retrieved_keys=[]
    for key in sorted(stimuli.keys()):
        retrieved = [i for i in em.execute(stimuli[key])]
        retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
        retrieved_keys.append(retrieved_key)
    assert retrieved_keys == [['F'], ['A'], ['A'], ['C'], ['B'], ['F']]

    stim = 'C'
    em.function.equidistant_keys_select = OLDEST
    retrieved = [i for i in em.function.get_memory(stimuli[stim][0])]
    retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
    assert retrieved_key == ['A']

    em.function.equidistant_keys_select = NEWEST
    retrieved = [i for i in em.function.get_memory(stimuli[stim][0])]
    retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
    assert retrieved_key == ['D']

    # Test that after allowing dups, warning is issued and memory with zeros is returned
    em.function.duplicate_keys_allowed = False
    stim = 'A'

    with pytest.warns(UserWarning) as warning_msg:
        retrieved = em.execute(stimuli[stim])
    warning_txt = warning_msg[0].message.args[0]
    assert 'More than one item matched key ([1 2 3]) in memory for ContentAddressableMemory' in str(warning_txt)
    retrieved_key = [k for k,v in stimuli.items() if v==list(retrieved)] or [None]
    assert retrieved_key == [None]
    assert retrieved[0] == [0, 0, 0]
    assert retrieved[1] == [0, 0, 0]

def test_ContentAddressableMemory_with_initializer_and_key_size_diff_from_val_size():

    stimuli = {'A': [[1,2,3],[4,5,6,7]],
               'B': [[8,9,10],[11,12,13,14]],
               'C': [[1,2,3],[11,12,13,14]],
               'D': [[1,2,3],[21,22,23,24]],
               'E': [[9,8,4],[11,12,13,14]],
               'F': [[10,10,30],[40,50,60,70]],
               }

    em = EpisodicMemoryMechanism(
            content_size=3,
            assoc_size=4,
            function = ContentAddressableMemory(
                    initializer=np.array([stimuli['F'], stimuli['F']]),
                    duplicate_keys_allowed=True,
                    equidistant_keys_select=RANDOM)
    )

    retrieved_keys=[]
    for key in sorted(stimuli.keys()):
        retrieved = [i for i in em.execute(stimuli[key])]
        retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
        retrieved_keys.append(retrieved_key)
    assert retrieved_keys == [['F'], ['A'], ['A'], ['C'], ['B'], ['F']]

    stim = 'C'
    em.function.equidistant_keys_select = OLDEST
    retrieved = [i for i in em.function.get_memory(stimuli[stim][0])]
    retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
    assert retrieved_key == ['A']

    em.function.equidistant_keys_select = NEWEST
    retrieved = [i for i in em.function.get_memory(stimuli[stim][0])]
    retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
    assert retrieved_key == ['D']

    # Test that after allowing dups, warning is issued and memory with zeros is returned
    em.function.duplicate_keys_allowed = False
    stim = 'A'

    with pytest.warns(UserWarning) as warning_msg:
        retrieved = em.execute(stimuli[stim])
    warning_txt = warning_msg[0].message.args[0]
    assert 'More than one item matched key ([1, 2, 3]) in memory for ContentAddressableMemory' in str(warning_txt)
    retrieved_key = [k for k,v in stimuli.items() if v==list(retrieved)] or [None]
    assert retrieved_key == [None]
    assert retrieved[0] == [0, 0, 0]
    assert retrieved[1] == [0, 0, 0, 0]

def test_ContentAddressableMemory_without_initializer_and_key_size_same_as_val_size():

    stimuli = {'A': [[1,2,3],[4,5,6]],
               'B': [[8,9,10],[11,12,13]],
               'C': [[1,2,3],[11,12,13]],
               'D': [[1,2,3],[21,22,23]],
               'E': [[9,8,4],[11,12,13]],
               'F': [[10,10,30],[40,50,60]],
               }

    em = EpisodicMemoryMechanism(
            content_size=3,
            assoc_size=3,
            function = ContentAddressableMemory(
                    duplicate_keys_allowed=True,
                    equidistant_keys_select=RANDOM)
    )

    retrieved_keys=[]
    for key in sorted(stimuli.keys()):
        retrieved = [i for i in em.execute(stimuli[key])]
        retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
        retrieved_keys.append(retrieved_key)
    assert retrieved_keys == [[None], ['A'], ['A'], ['C'], ['B'], ['C']]

    stim = 'C'
    em.function.equidistant_keys_select = OLDEST
    retrieved = [i for i in em.function.get_memory(stimuli[stim][0])]
    retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
    assert retrieved_key == ['A']

    em.function.equidistant_keys_select = NEWEST
    retrieved = [i for i in em.function.get_memory(stimuli[stim][0])]
    retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
    assert retrieved_key == ['D']

    # Test that after allowing dups, warning is issued and memory with zeros is returned
    em.function.duplicate_keys_allowed = False
    stim = 'A'

    with pytest.warns(UserWarning) as warning_msg:
        retrieved = em.execute(stimuli[stim])
    warning_txt = warning_msg[0].message.args[0]
    assert 'More than one item matched key ([1 2 3]) in memory for ContentAddressableMemory' in str(warning_txt)
    retrieved_key = [k for k,v in stimuli.items() if v==list(retrieved)] or [None]
    assert retrieved_key == [None]
    assert retrieved[0] == [0, 0, 0]
    assert retrieved[1] == [0, 0, 0]

def test_ContentAddressableMemory_without_initializer_and_key_size_diff_from_val_size():

    stimuli = {'A': [[1,2,3],[4,5,6,7]],
               'B': [[8,9,10],[11,12,13,14]],
               'C': [[1,2,3],[11,12,13,14]],
               'D': [[1,2,3],[21,22,23,24]],
               'E': [[9,8,4],[11,12,13,14]],
               'F': [[10,10,30],[40,50,60,70]],
               }

    em = EpisodicMemoryMechanism(
            content_size=3,
            assoc_size=4,
            function = ContentAddressableMemory(
                    duplicate_keys_allowed=True,
                    equidistant_keys_select=RANDOM)
    )

    retrieved_keys=[]
    for key in sorted(stimuli.keys()):
        retrieved = [i for i in em.execute(stimuli[key])]
        retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
        retrieved_keys.append(retrieved_key)
    assert retrieved_keys == [[None], ['A'], ['A'], ['C'], ['B'], ['C']]

    stim = 'C'
    em.function.equidistant_keys_select = OLDEST
    retrieved = [i for i in em.function.get_memory(stimuli[stim][0])]
    retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
    assert retrieved_key == ['A']

    em.function.equidistant_keys_select = NEWEST
    retrieved = [i for i in em.function.get_memory(stimuli[stim][0])]
    retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
    assert retrieved_key == ['D']

    # Test that after allowing dups, warning is issued and memory with zeros is returned
    em.function.duplicate_keys_allowed = False
    stim = 'A'

    with pytest.warns(UserWarning) as warning_msg:
        retrieved = em.execute(stimuli[stim])
    warning_txt = warning_msg[0].message.args[0]

    assert 'More than one item matched key ([1, 2, 3]) in memory for ContentAddressableMemory' in str(warning_txt)
    retrieved_key = [k for k,v in stimuli.items() if v==list(retrieved)] or [None]
    assert retrieved_key == [None]
    assert retrieved[0] == [0, 0, 0]
    assert retrieved[1] == [0, 0, 0, 0]


def test_ContentAddressableMemory_without_assoc():

    stimuli = {'A': [[1,2,3]],
               'B': [[8,9,10]],
               'C': [[1,2,3]],
               'D': [[1,2,3]],
               'E': [[9,8,4]],
               'F': [[10,10,30]],
               }

    em = EpisodicMemoryMechanism(
            name='EPISODIC MEMORY MECH',
            content_size=3,
            function = ContentAddressableMemory(
                    # initializer=np.array([stimuli['F'], stimuli['F']]),
                    duplicate_keys_allowed=True,
                    equidistant_keys_select=RANDOM,
                    retrieval_prob = 1.0
            )
    )

    for key in sorted(stimuli.keys()):
        print(f'\nCurrent memory: \n{em.memory}\n')
        retrieved = [i for i in em.execute(stimuli[key])]
        retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
        print(f'\nExecuted with stimulus {key}: {stimuli[key]};'
              f'\nRetrieved memory {retrieved_key[0]}: \n\t{retrieved}')

    retrieved_keys=[]
    for key in sorted(stimuli.keys()):
        retrieved = [i for i in em.execute(stimuli[key])]
        retrieved_key = [k for k,v in stimuli.items() if v==retrieved] or [None]
        retrieved_keys.append(retrieved_key)

    assert retrieved_keys == [['A', 'C', 'D'], ['B'], ['A', 'C', 'D'], ['A', 'C', 'D'], ['E'], ['F']]



