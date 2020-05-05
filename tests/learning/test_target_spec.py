import numpy as np
import pytest

from psyneulink.core.compositions.composition import Composition, RunError
from psyneulink.core.components.functions.distributionfunctions import NormalDist
from psyneulink.core.components.functions.learningfunctions import BackPropagation
from psyneulink.core.components.mechanisms.processing.transfermechanism import TransferMechanism
from psyneulink.core.components.process import Process
from psyneulink.core.components.system import System
from psyneulink.core.globals.keywords import ENABLED

class TestSimpleLearningPathway:

    def test_target_dict_spec_single_trial_scalar_and_lists_rl(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B")
        comp = Composition()
        learning_pathway = comp.add_reinforcement_learning_pathway(pathway=[A,B])
        target = learning_pathway.target
        comp.run(inputs={A: 1.0,
                      target:2.0})
        comp.run(inputs={A: 1.0,
                      target:[2.0]})
        comp.run(inputs={A: 1.0,
                      target:[[2.0]]})

        assert np.allclose(comp.results, [[[1.]], [[1.]], [[1.]]])

    def test_target_dict_spec_single_trial_scalar_and_lists_bp(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B")
        comp = Composition()
        learning_pathway = comp.add_reinforcement_learning_pathway(pathway=[A,B])
        target = learning_pathway.target
        comp.run(inputs={A: 1.0,
                      target:2.0})
        comp.run(inputs={A: 1.0,
                      target:[2.0]})
        comp.run(inputs={A: 1.0,
                      target:[[2.0]]})

        assert np.allclose(comp.results, [[[1.]], [[1.]], [[1.]]])

    def test_target_dict_spec_multi_trial_lists_rl(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B")

        comp = Composition()
        learning_pathway = comp.add_backpropagation_learning_pathway(pathway=[A,B])
        target = learning_pathway.target
        comp.run(inputs={A: [1.0, 2.0, 3.0],
                         target: [[4.0], [5.0], [6.0]]})
        comp.run(inputs={A: [1.0, 2.0, 3.0],
                         target: [[[4.0]], [[5.0]], [[6.0]]]})

        assert np.allclose(comp.results,
                            [[[1.]], [[2.]], [[3.]],
                             [[1.]], [[2.]], [[3.]]])

    def test_target_dict_spec_multi_trial_lists_bp(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B",
                              default_variable=[[0.0, 0.0]])

        comp = Composition()
        learning_pathway = comp.add_backpropagation_learning_pathway(pathway=[A,B])
        target = learning_pathway.target
        comp.run(inputs={A: 1.0,
                      target:[2.0, 3.0]})
        comp.run(inputs={A: 1.0,
                      target:[[2.0, 3.0]]})
        comp.run(inputs={A: [1.0, 2.0, 3.0],
                         target: [[3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]})
        comp.run(inputs={A: [1.0, 2.0, 3.0],
                         target: [[[3.0, 4.0]], [[5.0, 6.0]], [[7.0, 8.0]]]})

        assert np.allclose(comp.results,
                           [[[1., 1.]],
                            [[1., 1.]],
                            [[1., 1.]], [[2., 2.]], [[3., 3.]],
                            [[1., 1.]], [[2., 2.]], [[3., 3.]]])

        with pytest.raises(RunError) as error_text:
            comp.run(inputs={A: [1.0, 2.0, 3.0],
                             target: [[[3.0], [4.0]], [[5.0], [6.0]], [[7.0], [8.0]]]})
        assert ("Input stimulus" in str(error_text.value) and
                "for Target is incompatible with its external_input_values" in str(error_text.value))

    # def test_target_function_spec(self):
    #     A = TransferMechanism(name="multilayer-mech-A")
    #     B = TransferMechanism(name="multilayer-mech-B")
    #     C = TransferMechanism(name="multilayer-mech-C")
    #     comp = Composition()
    #     learning_pathway = comp.add_backpropagation_learning_pathway(pathway=[A,B,C])
    #     target = learning_pathway.target
    #     comp.run(inputs={A: 1.0,
    #                   target:2.0})
    #
    #     def target_function():
    #         val_1 = NormalDist(mean=3.0)()
    #         return val_1
    #
    #     S.run(inputs={A: 1.0},
    #           targets={C: target_function})

class TestMultilayerLearning:

    def test_dict_target_spec(self):
        A = TransferMechanism(name="multilayer-mech-A")
        B = TransferMechanism(name="multilayer-mech-B")
        C = TransferMechanism(name="multilayer-mech-comp")
        comp = Composition()
        learning_pathway = comp.add_backpropagation_learning_pathway(pathway=[A,B,C])
        target = learning_pathway.target
        comp.run(inputs={A: 1.0,
                      target:2.0})
        comp.run(inputs={A: 1.0,
                      target:[2.0]})
        comp.run(inputs={A: 1.0,
                      target:[[2.0]]})
        assert np.allclose(comp.results, [[[1.], [1.], [1.]]])

    def test_dict_target_spec_length2(self):
        A = TransferMechanism(name="multilayer-mech-A")
        B = TransferMechanism(name="multilayer-mech-B")
        C = TransferMechanism(name="multilayer-mech-C",
                              default_variable=[[0.0, 0.0]])
        comp = Composition()
        learning_pathway = comp.add_backpropagation_learning_pathway(pathway=[A,B,C])
        target = learning_pathway.target
        comp.run(inputs={A: 1.0,
                      target:[2.0, 3.0]})
        comp.run(inputs={A: 1.0,
                      target:[[2.0, 3.0]]})
        assert np.allclose(comp.results, [[1., 1.], [1., 1.]])

    def test_function_target_spec(self):
        A = TransferMechanism(name="multilayer-mech-A")
        B = TransferMechanism(name="multilayer-mech-B")
        C = TransferMechanism(name="multilayer-mech-C")
        comp = Composition()
        learning_pathway = comp.add_backpropagation_learning_pathway(pathway=[A,B,C])
        target = learning_pathway.target
        comp.run(inputs={A: 1.0,
                      target:2.0})

        def target_function():
            val_1 = NormalDist(mean=3.0)()
            return val_1

        S.run(inputs={A: 1.0},
              targets={C: target_function})

class TestDivergingLearningPathways:

    def test_dict_target_spec(self):
        A = TransferMechanism(name="diverging-learning-pathways-mech-A")
        B = TransferMechanism(name="diverging-learning-pathways-mech-B")
        C = TransferMechanism(name="diverging-learning-pathways-mech-C")
        D = TransferMechanism(name="diverging-learning-pathways-mech-D")
        E = TransferMechanism(name="diverging-learning-pathways-mech-E")

        P1 = Process(name="learning-pathway-1",
                     pathway=[A, B, C],
                     learning=ENABLED)
        P2 = Process(name="learning-pathway-2",
                    pathway=[A, D, E],
                    learning=ENABLED)

        S = System(name="learning-system",
                   processes=[P1, P2]
                   )

        S.run(inputs={A: 1.0},
              targets={C: 2.0,
                       E: 4.0})

        S.run(inputs={A: 1.0},
              targets={C: [2.0],
                       E: [4.0]})

        S.run(inputs={A: 1.0},
              targets={C: [[2.0]],
                       E: [[4.0]]})

    def test_dict_target_spec_length2(self):
        A = TransferMechanism(name="diverging-learning-pathways-mech-A")
        B = TransferMechanism(name="diverging-learning-pathways-mech-B")
        C = TransferMechanism(name="diverging-learning-pathways-mech-C",
                              default_variable=[[0.0, 0.0]])
        D = TransferMechanism(name="diverging-learning-pathways-mech-D")
        E = TransferMechanism(name="diverging-learning-pathways-mech-E",
                              default_variable=[[0.0, 0.0]])

        P1 = Process(name="learning-pathway-1",
                     pathway=[A, B, C],
                     learning=ENABLED)
        P2 = Process(name="learning-pathway-2",
                    pathway=[A, D, E],
                    learning=ENABLED)

        S = System(name="learning-system",
                   processes=[P1, P2]
                   )

        S.run(inputs={A: 1.0},
              targets={C: [2.0, 3.0],
                       E: [4.0, 5.0]})

        S.run(inputs={A: 1.0},
              targets={C: [[2.0, 3.0]],
                       E: [[4.0, 5.0]]})

    def test_dict_list_and_function(self):
        A = TransferMechanism(name="diverging-learning-pathways-mech-A")
        B = TransferMechanism(name="diverging-learning-pathways-mech-B")
        C = TransferMechanism(name="diverging-learning-pathways-mech-C")
        D = TransferMechanism(name="diverging-learning-pathways-mech-D")
        E = TransferMechanism(name="diverging-learning-pathways-mech-E")

        P1 = Process(name="learning-pathway-1",
                     pathway=[A, B, C],
                     learning=ENABLED)
        P2 = Process(name="learning-pathway-2",
                    pathway=[A, D, E],
                    learning=ENABLED)

        S = System(name="learning-system",
                   processes=[P1, P2]
                   )

        def target_function():
            val_1 = NormalDist(mean=3.0)()
            return val_1

        S.run(inputs={A: 1.0},
              targets={C: 2.0,
                       E: target_function})

        S.run(inputs={A: 1.0},
              targets={C: [2.0],
                       E: target_function})

        S.run(inputs={A: 1.0},
              targets={C: [[2.0]],
                       E: target_function})

class TestConvergingLearningPathways:

    def test_dict_target_spec(self):
        A = TransferMechanism(name="converging-learning-pathways-mech-A")
        B = TransferMechanism(name="converging-learning-pathways-mech-B")
        C = TransferMechanism(name="converging-learning-pathways-mech-C")
        D = TransferMechanism(name="converging-learning-pathways-mech-D")
        E = TransferMechanism(name="converging-learning-pathways-mech-E")

        P1 = Process(name="learning-pathway-1",
                     pathway=[A, B, C],
                     learning=ENABLED)
        P2 = Process(name="learning-pathway-2",
                    pathway=[D, E, C],
                    learning=ENABLED)

        S = System(name="learning-system",
                   processes=[P1, P2]
                   )

        S.run(inputs={A: 1.0,
                      D: 1.0},
              targets={C: 2.0})

        S.run(inputs={A: 1.0,
                      D: 1.0},
              targets={C: [2.0]})

        S.run(inputs={A: 1.0,
                      D: 1.0},
              targets={C: [[2.0]]})

    def test_dict_target_spec_length2(self):
        A = TransferMechanism(name="converging-learning-pathways-mech-A")
        B = TransferMechanism(name="converging-learning-pathways-mech-B")
        C = TransferMechanism(name="converging-learning-pathways-mech-C",
                              default_variable=[[0.0, 0.0]])
        D = TransferMechanism(name="converging-learning-pathways-mech-D")
        E = TransferMechanism(name="converging-learning-pathways-mech-E")

        P1 = Process(name="learning-pathway-1",
                     pathway=[A, B, C],
                     learning=ENABLED)
        P2 = Process(name="learning-pathway-2",
                    pathway=[D, E, C],
                    learning=ENABLED)

        S = System(name="learning-system",
                   processes=[P1, P2]
                   )

        S.run(inputs={A: 1.0,
                      D: 1.0},
              targets={C: [2.0, 3.0]})

        S.run(inputs={A: 1.0,
                      D: 1.0},
              targets={C: [[2.0, 3.0]]})

class TestInvalidTargetSpecs:

    def test_3_targets_4_inputs(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B")

        LP = Process(name="learning-process",
                     pathway=[A, B],
                     learning=ENABLED)

        S = System(name="learning-system",
                   processes=[LP],
                   )
        with pytest.raises(RunError) as error_text:
            S.run(inputs={A: [[[1.0]], [[2.0]], [[3.0]], [[4.0]]]},
                  targets={B: [[1.0], [2.0], [3.0]]})

        assert 'Number of target values specified (3) for each learning Pathway' in str(error_text.value) and \
               'must equal the number of input values specified (4)' in str(error_text.value)

    def test_2_target_mechanisms_1_dict_entry(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B")
        C = TransferMechanism(name="learning-process-mech-C")

        LP = Process(name="learning-process",
                     pathway=[A, B],
                     learning=ENABLED)
        LP2 = Process(name="learning-process2",
                     pathway=[A, C],
                     learning=ENABLED)

        S = System(name="learning-system",
                   processes=[LP, LP2],
                   )
        with pytest.raises(RunError) as error_text:

            S.run(inputs={A: [[[1.0]]]},
                  targets={B: [[1.0]]})

        assert 'missing from specification of targets for run' in str(error_text.value)

    def test_1_target_mechanisms_2_dict_entries(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B")
        C = TransferMechanism(name="learning-process-mech-C")

        LP = Process(name="learning-process",
                     pathway=[A, B, C],
                     learning=ENABLED)

        S = System(name="learning-system",
                   processes=[LP],
                   )

        with pytest.raises(RunError) as error_text:
            S.run(inputs={A: [[[1.0]]]},
                  targets={B: [[1.0]],
                           C: [[1.0]]})

        assert 'does not project to a target Mechanism in' in str(error_text.value)

    def test_2_target_mechanisms_list_spec(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B")
        C = TransferMechanism(name="learning-process-mech-C")

        LP = Process(name="learning-process",
                     pathway=[A, B],
                     learning=ENABLED)
        LP2 = Process(name="learning-process2",
                     pathway=[A, C],
                     learning=ENABLED)

        S = System(name="learning-system",
                   processes=[LP, LP2],
                   )
        with pytest.raises(RunError) as error_text:

            S.run(inputs={A: [[[1.0]]]},
                  targets=[[1.0]])

        assert 'Target values for' in str(error_text.value) and \
               'must be specified in a dictionary' in str(error_text.value)

    def test_2_target_mechanisms_fn_spec(self):
        A = TransferMechanism(name="learning-process-mech-A")
        B = TransferMechanism(name="learning-process-mech-B")
        C = TransferMechanism(name="learning-process-mech-C")

        LP = Process(name="learning-process",
                     pathway=[A, B],
                     learning=ENABLED)
        LP2 = Process(name="learning-process2",
                     pathway=[A, C],
                     learning=ENABLED)

        S = System(name="learning-system",
                   processes=[LP, LP2],
                   )

        def target_function():
            val_1 = NormalDist(mean=3.0)()
            val_2 = NormalDist(mean=3.0)()
            return [val_1, val_2]

        with pytest.raises(RunError) as error_text:

            S.run(inputs={A: [[[1.0]]]},
                  targets=target_function)

        assert 'Target values for' in str(error_text.value) and \
               'must be specified in a dictionary' in str(error_text.value)
