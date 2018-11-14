import numpy as np
import psyneulink as pnl
import pytest

import psyneulink.core.globals.utilities


class TestModels:

    # This implements the model by Cohen, J. D., & Huston, T. A. (1994). Progress in the use of interactive
    # models for understanding attention and performance. In C. Umilta & M. Moscovitch(Eds.),
    # AttentionandperformanceXV(pp.453-456). Cam- bridge, MA: MIT Press.
    # The model aims to capute top-down effects of selective attention and the bottom-up effects of attentional capture.

    def test_cohen_huston_1994(self):

        # Define Variables -------------------------------------------------------------------------------------
        rate = 0.1  # modified from the original code from 0.01 to 0.1
        inhibition = -2.0  # lateral inhibition
        bias = 4.0  # bias is positive since Logistic equation has - sing already implemented
        threshold = 0.55  # modified from original code from 0.6 to 0.55 because incongruent condition won't reach 0.6
        settle_trials = 50  # cycles until model settles

        # Create mechanisms ------------------------------------------------------------------------------------

        #   Linear input units, colors: ('red', 'green'), words: ('RED','GREEN')

        colors_input_layer = pnl.TransferMechanism(
            size=3,
            function=pnl.Linear,
            name='COLORS_INPUT'
        )

        words_input_layer = pnl.TransferMechanism(
            size=3,
            function=pnl.Linear,
            name='WORDS_INPUT'
        )

        task_input_layer = pnl.TransferMechanism(
            size=2,
            function=pnl.Linear,
            name='TASK_INPUT'
        )

        #   Task layer, tasks: ('name the color', 'read the word')
        task_layer = pnl.RecurrentTransferMechanism(
            size=2,
            function=pnl.Logistic(),
            hetero=-2,
            integrator_mode=True,
            integration_rate=0.1,
            name='TASK'
        )

        #   Hidden layer units, colors: ('red','green') words: ('RED','GREEN')
        colors_hidden_layer = pnl.RecurrentTransferMechanism(
            size=3,
            function=pnl.Logistic(x_0=4.0),
            integrator_mode=True,
            hetero=-2.0,
            # noise=pnl.NormalDist(mean=0.0, standard_deviation=.0).function,
            integration_rate=0.1,  # cohen-huston text says 0.01
            name='COLORS HIDDEN'
        )

        words_hidden_layer = pnl.RecurrentTransferMechanism(
            size=3,
            function=pnl.Logistic(x_0=4.0),
            hetero=-2,
            integrator_mode=True,
            # noise=pnl.NormalDist(mean=0.0, standard_deviation=.05).function,
            integration_rate=0.1,
            name='WORDS HIDDEN'
        )
        #   Response layer, responses: ('red', 'green'): RecurrentTransferMechanism for self inhibition matrix
        response_layer = pnl.RecurrentTransferMechanism(
            size=2,
            function=pnl.Logistic(),
            hetero=-2.0,
            integrator_mode=True,
            integration_rate=0.1,
            name='RESPONSE'
        )
        # Connect mechanisms --------------------------------------------------------------------------------------------------
        # (note that response layer projections are set to all zero first for initialization

        color_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0]
            ])
        )

        word_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0]
            ])
        )

        task_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.0, 0.0],
                [0.0, 1.0]
            ])
        )

        color_task_weights = pnl.MappingProjection(
            matrix=np.array([
                [4.0, 0.0],
                [4.0, 0.0],
                [4.0, 0.0]
            ])
        )

        task_color_weights = pnl.MappingProjection(
            matrix=np.array([
                [4.0, 4.0, 4.0],
                [0.0, 0.0, 0.0]
            ])
        )

        word_task_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 4.0],
                [0.0, 4.0],
                [0.0, 4.0]
            ])
        )

        task_word_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0, 0.0],
                [4.0, 4.0, 4.0]
            ])
        )

        response_color_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0]
            ])
        )

        response_word_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0]
            ])
        )

        color_response_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.5, 0.0],
                [0.0, 1.5],
                [0.0, 0.0]
            ])
        )
        word_response_weights = pnl.MappingProjection(
            matrix=np.array([
                [2.5, 0.0],
                [0.0, 2.5],
                [0.0, 0.0]
            ])
        )
        bidirectional_stroop = pnl.Composition(name="bidirectional_stroop")

        color_response_pathway = [colors_input_layer,
                                  color_input_weights,
                                  colors_hidden_layer,
                                  color_response_weights,
                                  response_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=color_response_pathway)

        color_response_pathway_2 = [response_layer,
                                    response_color_weights,
                                    colors_hidden_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=color_response_pathway_2)


        word_response_pathway = [words_input_layer,
                                 word_input_weights,
                                 words_hidden_layer,
                                 word_response_weights,
                                 response_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=word_response_pathway)

        word_response_pathway_2 = [response_layer,
                                   response_word_weights,
                                   words_hidden_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=word_response_pathway_2)


        task_color_response_pathway = [task_input_layer,
                                       task_input_weights,
                                       task_layer,
                                       task_color_weights,
                                       colors_hidden_layer]

        bidirectional_stroop.add_linear_processing_pathway(pathway=task_color_response_pathway)

        task_color_response_pathway_2 = [colors_hidden_layer,
                                         color_task_weights,
                                         task_layer]

        bidirectional_stroop.add_linear_processing_pathway(pathway=task_color_response_pathway_2)

        task_word_response_pathway = [task_input_layer,
                                      task_layer,
                                      task_word_weights,
                                      words_hidden_layer]
        bidirectional_stroop.add_linear_processing_pathway(pathway=task_word_response_pathway)

        task_word_response_pathway_2 = [words_hidden_layer,
                                        word_task_weights,
                                        task_layer]

        bidirectional_stroop.add_linear_processing_pathway(pathway=task_word_response_pathway_2)
        bidirectional_stroop.add_required_c_node_role(response_layer, psyneulink.core.globals.utilities.CNodeRole.TERMINAL)
        bidirectional_stroop._analyze_graph()

        input_dict = {colors_input_layer: [0, 0, 0],
                      words_input_layer: [0, 0, 0],
                      task_input_layer: [0, 1]}

        bidirectional_stroop.run(inputs=input_dict)
        # print(bidirectional_stroop.get_c_nodes_by_role(pnl.CNodeRole.TERMINAL))
        # print(bidirectional_stroop.output_values)
        # for node in bidirectional_stroop.c_nodes:
        #     print(node.name, " Value: ", node.output_values)

    def test_DDM(self):
        myMechanism = pnl.DDM(
            function=pnl.BogaczEtAl(
                drift_rate=(1.0),
                threshold=(10.0),
                starting_point=0.0,
            ),
            name='My_DDM',
        )

        myMechanism_2 = pnl.DDM(
            function=pnl.BogaczEtAl(
                drift_rate=2.0,
                threshold=20.0),
            name='My_DDM_2'
        )

        myMechanism_3 = pnl.DDM(
            function=pnl.BogaczEtAl(
                drift_rate=3.0,
                threshold=30.0
            ),
            name='My_DDM_3',
        )

        z = pnl.Composition()
        z.add_linear_processing_pathway([myMechanism,
                                        pnl.MappingProjection(matrix=pnl.IDENTITY_MATRIX),
                                        myMechanism_2,
                                         pnl.MappingProjection(matrix=pnl.FULL_CONNECTIVITY_MATRIX),
                                        myMechanism_3])

        result = z.run(inputs={myMechanism: [[40]]})[0][0]

        expected_output = [
            (myMechanism.input_states[0].parameters.value.get(z), np.array([40.])),
            (myMechanism.output_states[0].parameters.value.get(z), np.array([10.])),
            (myMechanism_2.input_states[0].parameters.value.get(z), np.array([10.])),
            (myMechanism_2.output_states[0].parameters.value.get(z), np.array([20.])),
            (myMechanism_3.input_states[0].parameters.value.get(z), np.array([20.])),
            (myMechanism_3.output_states[0].parameters.value.get(z), np.array([30.])),
            (result, np.array([30.])),
        ]

        for i in range(len(expected_output)):
            val, expected = expected_output[i]
            # setting absolute tolerance to be in accordance with reference_output precision
            # if you do not specify, assert_allcose will use a relative tolerance of 1e-07,
            # which WILL FAIL unless you gather higher precision values to use as reference
            np.testing.assert_allclose(val, expected, atol=1e-08, err_msg='Failed on expected_output[{0}]'.format(i))

    def test_lauras_cohen_1990_model(self):
        #  INPUT UNITS

        #  colors: ('red', 'green'), words: ('RED','GREEN')
        colors_input_layer = pnl.TransferMechanism(size=2,
                                                   function=pnl.Linear,
                                                   name='COLORS_INPUT')

        words_input_layer = pnl.TransferMechanism(size=2,
                                                  function=pnl.Linear,
                                                  name='WORDS_INPUT')

        #   Task layer, tasks: ('name the color', 'read the word')
        task_layer = pnl.TransferMechanism(size=2,
                                           function=pnl.Linear,
                                           name='TASK')

        #   HIDDEN LAYER UNITS

        #   colors_hidden: ('red','green')
        #   Logistic activation function, Gain = 1.0, Bias = -4.0 (in PNL bias is subtracted so enter +4.0 to get negative bias)
        #   randomly distributed noise to the net input
        #   time averaging = integration_rate = 0.1
        unit_noise = 0.005
        colors_hidden_layer = pnl.TransferMechanism(size=2,
                                                    function=pnl.Logistic(gain=1.0, x_0=4.0),
                                                    # should be able to get same result with offset = -4.0
                                                    integrator_mode=True,
                                                    noise=pnl.NormalDist(mean=0, standard_deviation=unit_noise).function,
                                                    integration_rate=0.1,
                                                    name='COLORS HIDDEN')
        #    words_hidden: ('RED','GREEN')
        words_hidden_layer = pnl.TransferMechanism(size=2,
                                                   function=pnl.Logistic(gain=1.0, x_0=4.0),
                                                   integrator_mode=True,
                                                   noise=pnl.NormalDist(mean=0, standard_deviation=unit_noise).function,
                                                   integration_rate=0.1,
                                                   name='WORDS HIDDEN')

        #    OUTPUT UNITS

        #   Response layer, provide input to accumulator, responses: ('red', 'green')
        #   time averaging = tau = 0.1
        #   randomly distributed noise to the net input
        response_layer = pnl.TransferMechanism(size=2,
                                               function=pnl.Logistic,
                                               name='RESPONSE',
                                               integrator_mode=True,
                                               noise=pnl.NormalDist(mean=0, standard_deviation=unit_noise).function,
                                               integration_rate=0.1)
        #   Respond red accumulator
        #   alpha = rate of evidence accumlation = 0.1
        #   sigma = noise = 0.1
        #   noise will be: squareroot(time_step_size * noise) * a random sample from a normal distribution
        accumulator_noise = 0.1
        respond_red_accumulator = pnl.IntegratorMechanism(function=pnl.SimpleIntegrator(noise=pnl.NormalDist(mean=0,
                                                                                                             standard_deviation=accumulator_noise).function,
                                                                                        rate=0.1),
                                                          name='respond_red_accumulator')
        #   Respond green accumulator
        respond_green_accumulator = pnl.IntegratorMechanism(function=pnl.SimpleIntegrator(noise=pnl.NormalDist(mean=0,
                                                                                                               standard_deviation=accumulator_noise).function,
                                                                                          rate=0.1),
                                                            name='respond_green_accumulator')

        #   LOGGING
        colors_hidden_layer.set_log_conditions('value')
        words_hidden_layer.set_log_conditions('value')
        response_layer.set_log_conditions('value')
        respond_red_accumulator.set_log_conditions('value')
        respond_green_accumulator.set_log_conditions('value')

        #   SET UP CONNECTIONS

        #   rows correspond to sender
        #   columns correspond to: weighting of the contribution that a given sender makes to the receiver

        #   INPUT TO HIDDEN
        # row 0: input_'red' to hidden_'red', hidden_'green'
        # row 1: input_'green' to hidden_'red', hidden_'green'
        color_weights = pnl.MappingProjection(matrix=np.matrix([[2.2, -2.2],
                                                                [-2.2, 2.2]]),
                                              name='COLOR_WEIGHTS')
        # row 0: input_'RED' to hidden_'RED', hidden_'GREEN'
        # row 1: input_'GREEN' to hidden_'RED', hidden_'GREEN'
        word_weights = pnl.MappingProjection(matrix=np.matrix([[2.6, -2.6],
                                                               [-2.6, 2.6]]),
                                             name='WORD_WEIGHTS')

        #   HIDDEN TO RESPONSE
        # row 0: hidden_'red' to response_'red', response_'green'
        # row 1: hidden_'green' to response_'red', response_'green'
        color_response_weights = pnl.MappingProjection(matrix=np.matrix([[1.3, -1.3],
                                                                         [-1.3, 1.3]]),
                                                       name='COLOR_RESPONSE_WEIGHTS')
        # row 0: hidden_'RED' to response_'red', response_'green'
        # row 1: hidden_'GREEN' to response_'red', response_'green'
        word_response_weights = pnl.MappingProjection(matrix=np.matrix([[2.5, -2.5],
                                                                        [-2.5, 2.5]]),
                                                      name='WORD_RESPONSE_WEIGHTS')

        #   TASK TO HIDDEN LAYER
        #   row 0: task_CN to hidden_'red', hidden_'green'
        #   row 1: task_WR to hidden_'red', hidden_'green'
        task_CN_weights = pnl.MappingProjection(matrix=np.matrix([[4.0, 4.0],
                                                                  [0, 0]]),
                                                name='TASK_CN_WEIGHTS')

        #   row 0: task_CN to hidden_'RED', hidden_'GREEN'
        #   row 1: task_WR to hidden_'RED', hidden_'GREEN'
        task_WR_weights = pnl.MappingProjection(matrix=np.matrix([[0, 0],
                                                                  [4.0, 4.0]]),
                                                name='TASK_WR_WEIGHTS')

        #   RESPONSE UNITS TO ACCUMULATORS
        #   row 0: response_'red' to respond_red_accumulator
        #   row 1: response_'green' to respond_red_accumulator
        respond_red_differencing_weights = pnl.MappingProjection(matrix=np.matrix([[1.0], [-1.0]]),
                                                                 name='RESPOND_RED_WEIGHTS')

        #   row 0: response_'red' to respond_green_accumulator
        #   row 1: response_'green' to respond_green_accumulator
        respond_green_differencing_weights = pnl.MappingProjection(matrix=np.matrix([[-1.0], [1.0]]),
                                                                   name='RESPOND_GREEN_WEIGHTS')

        my_Stroop = pnl.Composition()

        #   CREATE PATHWAYS
        #   Words pathway
        words_pathway = [words_input_layer,
                         word_weights,
                         words_hidden_layer,
                         word_response_weights,
                         response_layer]
        my_Stroop.add_linear_processing_pathway(words_pathway)

        #   Colors pathway
        colors_pathway = [colors_input_layer,
                          color_weights,
                          colors_hidden_layer,
                          color_response_weights,
                          response_layer]
        my_Stroop.add_linear_processing_pathway(colors_pathway)

        #   Task representation pathway
        task_CN_pathway = [task_layer,
                           task_CN_weights,
                           colors_hidden_layer]
        my_Stroop.add_linear_processing_pathway(task_CN_pathway)

        #   Task representation pathway
        task_WR_pathway = [task_layer,
                           task_WR_weights,
                           words_hidden_layer]
        my_Stroop.add_linear_processing_pathway(task_WR_pathway)

        #   Evidence accumulation pathway
        respond_red_pathway = [response_layer,
                               respond_red_differencing_weights,
                               respond_red_accumulator]
        my_Stroop.add_linear_processing_pathway(respond_red_pathway)

        respond_green_pathway = [response_layer,
                                 respond_green_differencing_weights,
                                 respond_green_accumulator]
        my_Stroop.add_linear_processing_pathway(respond_green_pathway)

        # Function to create test trials
        # a RED word input is [1,0] to words_input_layer and GREEN word is [0,1]
        # a red color input is [1,0] to colors_input_layer and green color is [0,1]
        # a color-naming trial is [1,0] to task_layer and a word-reading trial is [0,1]

        def trial_dict(red_color, green_color, red_word, green_word, CN, WR):

            trialdict = {
                colors_input_layer: [red_color, green_color],
                words_input_layer: [red_word, green_word],
                task_layer: [CN, WR]
            }
            return trialdict

        #   CREATE THRESHOLD FUNCTION
        # first value of DDM's value is DECISION_VARIABLE
        def pass_threshold(mech1, mech2, thresh, execution_id=None):
            results1 = mech1.output_states[0].parameters.value.get(execution_id)
            results2 = mech2.output_states[0].parameters.value.get(execution_id)
            for val in results1:
                if val >= thresh:
                    return True
            for val in results2:
                if val >= thresh:
                    return True
            return False

        accumulator_threshold = 1.0

        mechanisms_to_update = [colors_hidden_layer, words_hidden_layer, response_layer]

        def switch_integrator_mode(mechanisms, mode):
            for mechanism in mechanisms:
                mechanism.integrator_mode = mode

        def switch_noise(mechanisms, noise):
            for mechanism in mechanisms:
                mechanism.noise = noise

        def switch_to_initialization_trial(mechanisms):
            # Turn off accumulation
            switch_integrator_mode(mechanisms, False)
            # Turn off noise
            switch_noise(mechanisms, 0)
            # Execute once per trial
            my_Stroop.termination_processing = {pnl.TimeScale.TRIAL: pnl.AllHaveRun()}

        def switch_to_processing_trial(mechanisms):
            # Turn on accumulation
            switch_integrator_mode(mechanisms, True)
            # Turn on noise
            switch_noise(mechanisms, pnl.NormalDist(mean=0, standard_deviation=unit_noise).function)
            # Execute until one of the accumulators crosses the threshold
            my_Stroop.termination_processing = {pnl.TimeScale.TRIAL: pnl.While(pass_threshold,
                                                                               respond_red_accumulator,
                                                                               respond_green_accumulator,
                                                                               accumulator_threshold)}

        def switch_trial_type():
            # Next trial will be a processing trial
            if isinstance(my_Stroop.termination_processing[pnl.TimeScale.TRIAL], pnl.AllHaveRun):
                switch_to_processing_trial(mechanisms_to_update)
            # Next trial will be an initialization trial
            else:
                switch_to_initialization_trial(mechanisms_to_update)

        CN_trial_initialize_input = trial_dict(0, 0, 0, 0, 1, 0)

        WR_trial_initialize_input = trial_dict(0, 0, 0, 0, 0, 1)

        # Start with an initialization trial
        switch_to_initialization_trial(mechanisms_to_update)

        my_Stroop.run(inputs=trial_dict(0, 1, 1, 0, 1, 0),
                      # termination_processing=change_termination_processing,
                      num_trials=4,
                      call_after_trial=switch_trial_type
                      )

        # {colors_input_layer: [[0, 0], [1, 0]],
        #                       words_input_layer: [[0, 0], [1, 0]],
        #                       task_layer: [[0, 1], [0, 1]]}

    # Implements the Kalanthroff, Davelaar, Henik, Goldfarb & Usher model: Task Conflict and Proactive Control:
    # A Computational Theory of the Stroop Task. Psychol Rev. 2018 Jan;125(1):59-82. doi: 10.1037/rev0000083.
    # Epub 2017 Oct 16.
    # #https://www.ncbi.nlm.nih.gov/pubmed/29035077

    def test_kalanthroff(self):

        # Define Variables ------------------------------------------------------------------------------------------
        Lambda = 0.03  # PsyNeuLink has Euler integration constant reversed (1-0.97)
        pc_high = 0.15  # High proactive control from Figure 6 in Paper
        pc_low = 0.025  # Low proactive control from Figure 6 in Paper
        pc = pc_low  # Select proactive control
        inhibition = -1.3  # Inhibition between units within a layer
        inhibition_task = -1.9  # Inhibition between units within task layer
        bias = -0.3  # bias input to color feature layer and word feature layer
        threshold = 0.70
        settle = 200  # Number of trials until system settles

        # Create mechanisms -----------------------------------------------------------------------------------------
        # 4 Input layers for color, word, task & bias
        colors_input_layer = pnl.TransferMechanism(
            size=2,
            function=pnl.Linear,
            name='COLORS_INPUT'
        )

        words_input_layer = pnl.TransferMechanism(
            size=2,
            function=pnl.Linear,
            name='WORDS_INPUT'
        )

        task_input_layer = pnl.TransferMechanism(
            size=2,
            function=pnl.Linear,
            name='PROACTIVE_CONTROL'
        )

        bias_input = pnl.TransferMechanism(
            size=2,
            function=pnl.Linear,
            name='BIAS'
        )

        # Built python function to ensure that the logistic function outputs 0 when input is <= 0

        def my_special_Logistic(variable):
            maxi = variable - 0.0180
            output = np.fmax([0], maxi)
            return output

        # Built python function that takes output of special logistic function and computes conflict by multiplying
        # output both task units with each over times 500

        def my_conflict_function(variable):
            maxi = variable - 0.0180
            new = np.fmax([0], maxi)
            out = [new[0] * new[1] * 500]
            return out

        # Create color feature layer, word feature layer, task demand layer and response layer
        color_feature_layer = pnl.RecurrentTransferMechanism(
            size=2,  # Define unit size
            function=pnl.Logistic(gain=4, x_0=1),  # to 4 & bias to 1
            integrator_mode=True,  # Set Integrator mode to True
            integration_rate=Lambda,  # smoothing factor ==  integration rate
            hetero=inhibition,  # Inhibition among units within a layer
            output_states=[{  # Create new output state by applying
                pnl.NAME: 'SPECIAL_LOGISTIC',  # the "my_special_Logistic" function
                pnl.VARIABLE: (pnl.OWNER_VALUE, 0),
                pnl.FUNCTION: my_special_Logistic
            }],
            name='COLOR_LAYER')

        # The word_feature_layer is set up as the color_feature_layer
        word_feature_layer = pnl.RecurrentTransferMechanism(
            size=2,  # Define unit size
            function=pnl.Logistic(gain=4, x_0=1),  # to 4 & bias to 1
            integrator_mode=True,  # Set Integrator mode to True
            integration_rate=Lambda,  # smoothing factor ==  integration rate
            hetero=inhibition,  # Inhibition among units within a layer
            output_states=[{  # Create new output state by applying
                pnl.NAME: 'SPECIAL_LOGISTIC',  # the "my_special_Logistic" function
                pnl.VARIABLE: (pnl.OWNER_VALUE, 0),
                pnl.FUNCTION: my_special_Logistic
            }],
            name='WORD_LAYER')

        # The response_layer is set up as the color_feature_layer & the word_feature_layer
        response_layer = pnl.RecurrentTransferMechanism(
            size=2,  # Define unit size
            function=pnl.Logistic(gain=4, x_0=1),  # to 4 & bias to 1
            integrator_mode=True,  # Set Integrator mode to True
            integration_rate=Lambda,  # smoothing factor ==  integration rate
            hetero=inhibition,  # Inhibition among units within a layer
            output_states=[{  # Create new output state by applying
                pnl.NAME: 'SPECIAL_LOGISTIC',  # the "my_special_Logistic" function
                pnl.VARIABLE: (pnl.OWNER_VALUE, 0),
                pnl.FUNCTION: my_special_Logistic
            }],
            name='RESPONSE_LAYER'
        )

        # The task_demand_layer is set up as the color_feature_layer but with a different python function on it's output state
        # and a differnet inhibition weight on the hetero
        task_demand_layer = pnl.RecurrentTransferMechanism(
            size=2,  # Define unit size
            function=pnl.Logistic(gain=4, x_0=1),  # to 4 & bias to 1
            integrator_mode=True,  # Set Integrator mode to True
            integration_rate=Lambda,  # smoothing factor ==  integration rate
            hetero=inhibition_task,  # Inhibition among units within a layer
            output_states=[  # Create new output state by applying
                {
                    pnl.NAME: 'SPECIAL_LOGISTIC',  # the "my_conflict_function" function
                    pnl.VARIABLE: (pnl.OWNER_VALUE, 0),
                    pnl.FUNCTION: my_special_Logistic
                },
                {
                    pnl.NAME: 'CONFLICT',
                    pnl.VARIABLE: (pnl.OWNER_VALUE, 0),
                    pnl.FUNCTION: my_conflict_function
                }
            ],
            name='TASK_LAYER'
        )

        # Log mechanisms ------------------------------------------------------------------------------------------------------
        color_feature_layer.set_log_conditions('SPECIAL_LOGISTIC')  # Log output of my_special_Logistic function
        word_feature_layer.set_log_conditions('SPECIAL_LOGISTIC')  # Log output of my_special_Logistic function
        response_layer.set_log_conditions('SPECIAL_LOGISTIC')  # Log output of my_special_Logistic function
        task_demand_layer.set_log_conditions('SPECIAL_LOGISTIC')  # Log output of my_special_Logistic function

        task_demand_layer.set_log_conditions('CONFLICT')  # Log outout of my_conflict_function function

        # Connect mechanisms --------------------------------------------------------------------------------------------------
        color_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0],  # response layer projections are set to all
                [0.0, 0.0]  # zero for initialization period first
            ])
        )
        word_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0],
                [0.0, 0.0]
            ])
        )
        color_task_weights = pnl.MappingProjection(
            matrix=np.array([
                [2.0, 0.0],  # color to task projection
                [2.0, 0.0]
            ])
        )
        word_task_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 2.0],  # word to task projection
                [0.0, 2.0]
            ])
        )
        task_color_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.0, 1.0],  # task to color projection
                [0.0, 0.0]
            ])
        )
        task_word_weights = pnl.MappingProjection(
            matrix=np.array([
                [0.0, 0.0],  # task to word projection
                [1.0, 1.0]
            ])
        )
        color_response_weights = pnl.MappingProjection(
            matrix=np.array([
                [2.0, 0.0],  # color to response projection
                [0.0, 2.0]
            ])
        )
        word_response_weights = pnl.MappingProjection(
            matrix=np.array([
                [2.5, 0.0],  # word to response projection
                [0.0, 2.5]
            ])
        )
        task_input_weights = pnl.MappingProjection(
            matrix=np.array([
                [1.0, 0.0],  # proactive control to task
                [0.0, 1.0]
            ])
        )

        # to send a control signal from the task demand layer to the response layer,
        # set matrix to -1 to reduce response layer activation
        # specify the sender of the projection which is the second output state the task demand layer
        # specify the receiver of the projection
        task_conflict_to_response_weights = pnl.MappingProjection(
            matrix=np.array([[-1.0, -1.0]]),
            sender=task_demand_layer.output_states[1],
            receiver=response_layer
        )

        # Create pathways -----------------------------------------------------------------------------------------------------
        color_response_pathway = [colors_input_layer,
                                  color_input_weights,
                                  color_feature_layer,
                                  color_response_weights,
                                  response_layer]

        word_response_pathway = [words_input_layer,
                                 word_input_weights,
                                 word_feature_layer,
                                 word_response_weights,
                                 response_layer]

        task_pathway = [task_input_layer,
                        task_input_weights,
                        task_demand_layer]

        task_color_pathway_1 = [task_demand_layer,
                                task_color_weights,
                                color_feature_layer]

        task_color_pathway_2 = [color_feature_layer,
                                color_task_weights,
                                task_demand_layer]

        task_word_pathway_1 = [task_demand_layer,
                               task_word_weights,
                               word_feature_layer]

        task_word_pathway_2 = [word_feature_layer,
                               word_task_weights,
                               task_demand_layer]

        bias_color_pathway = [bias_input, color_feature_layer]

        bias_word_pathway = [bias_input, word_feature_layer]

        conflict_pathway = [task_demand_layer,
                            task_conflict_to_response_weights,
                            response_layer]

        PCTC = pnl.Composition(name="PCTC")

        composition_pathways = [color_response_pathway,
                                word_response_pathway,
                                task_pathway,
                                task_color_pathway_1,
                                task_word_pathway_1,
                                task_color_pathway_2,
                                task_word_pathway_2,
                                bias_color_pathway,
                                bias_word_pathway,
                                conflict_pathway]

        for pathway in composition_pathways:
            PCTC.add_linear_processing_pathway(pathway)

        def pass_threshold(response_layer, thresh, execution_id=None):
            results1 = response_layer.output_state.parameters.value.get(execution_id)[0]  # red response
            results2 = response_layer.output_state.parameters.value.get(execution_id)[1]  # green response
            if results1 >= thresh or results2 >= thresh:
                return True
            return False

        terminate_trial = {
            pnl.TimeScale.TRIAL: pnl.While(pass_threshold, response_layer, threshold),
            pnl.TimeScale.RUN: pnl.Never()
        }

        # Create test trials function -----------------------------------------------------------------------
        # a BLUE word input is [1,0] to words_input_layer and GREEN word is [0,1]
        # a blue color input is [1,0] to colors_input_layer and green color is [0,1]
        # a color-naming trial is [1,0] to task_layer and a word-reading trial is [0,1]


        def trial_dict(blue_color, green_color, blue_word, green_word, PC_CN, PC_WR, bias):

            trialdict = {
                colors_input_layer: [blue_color, green_color],
                words_input_layer: [blue_word, green_word],
                task_input_layer: [PC_CN, PC_WR],
                bias_input: [bias, bias]
            }
            return trialdict

        initialize_input = trial_dict(1.0, 0.0, 1.0, 0.0, pc, 0.0, bias)

        # Run congruent trial --------------------------------------------------------------------------------
        congruent_input = trial_dict(1.0, 0.0, 1.0, 0.0, pc, 0.0, bias)  # specify congruent trial input
        results_1 = PCTC.run(inputs=initialize_input,
                             num_trials=settle)  # run system to settle for 200 trials with congruent stimuli input

        # results_1 is all zeros due to output state function
        #
        # assert np.allclose(words_input_layer.value, [[1., 0.]])
        # assert np.allclose(word_feature_layer.value, [[0.00550112, 0.00550112]])
        # assert np.allclose(response_layer.value, [[0.01798621, 0.01798621]])
        # assert np.allclose(colors_input_layer.value, [[1., 0.]])
        # assert np.allclose(color_feature_layer.value,  [[0.00554086,  0.00554086]])
        # assert np.allclose(task_input_layer.value, [[0.025, 0.]])
        # assert np.allclose(task_demand_layer.value, [[0.01983591, 0.01774496]])
        # assert np.allclose(bias_input.value, [[-0.3, -0.3]])

        color_input_weights.matrix = np.array([
            [1.0, 0.0],  # set color input projections to 1 on the diagonals to e.g.
            [0.0, 1.0]
        ])  # send a green color input to the green unit of the color layer
        word_input_weights.matrix = np.array([
            [1.0, 0.0],  # the same for word input projections
            [0.0, 1.0]
        ])

        # KDM 8/23/18: below must be added because these were expected to be changed with the above matrix setting, but this has appeared
        # to be incorrect behavior, and the reason for doing it is unknown
        color_input_weights.parameter_states['matrix'].function_object.parameters.previous_value.set(color_input_weights.matrix, PCTC, override=True)
        word_input_weights.parameter_states['matrix'].function_object.parameters.previous_value.set(word_input_weights.matrix, PCTC, override=True)

        results_2 = PCTC.run(inputs=congruent_input,
                             termination_processing=terminate_trial)  # run system with congruent stimulus input until
        # assert np.allclose(words_input_layer.value, [[1., 0.]])
        # assert np.allclose(word_feature_layer.value, [[0.23271063, 0.0017892]],  rtol=1e-02)
        # assert np.allclose(response_layer.value, [[0.72332318, 0.00110829]], rtol=1e-02)
        # assert np.allclose(colors_input_layer.value, [[1., 0.]])
        # assert np.allclose(color_feature_layer.value, [[0.50484897, 0.00194202]], rtol=1e-02)
        # assert np.allclose(task_input_layer.value, [[0.025, 0.]])
        # assert np.allclose(task_demand_layer.value, [[0.39605925, 0.01018448]], rtol=1e-02)
        # assert np.allclose(bias_input.value, [[-0.3, -0.3]])

    # This script implements Figure 1 of Botvinick, M. M., Braver, T. S., Barch, D. M., Carter, C. S., & Cohen, J. D. (2001).
    # Conflict monitoring and cognitive control. Psychological Review, 108, 624–652.
    # http://dx.doi.org/10.1037/0033-295X.108.3.624

    # Figure 1 plots the ENERGY computed by a conflict mechanism. It is highest for incongruent trials,
    # and similar for congruent and neutral trials.
    # Noise is turned of and for each condition we ran one trial only. A response threshold was not defined. Responses were
    # made at the marked * signs in the figure.
    # Note that this script implements a slightly different Figure than in the original Figure in the paper.
    # However, this implementation is identical with a plot we created with an old MATLAB code which was used for the
    # conflict monitoring simulations.


    # def test_botvinick_model(self):
    #
    #     colors_input_layer = pnl.TransferMechanism(size=3,
    #                                                function=pnl.Linear,
    #                                                name='COLORS_INPUT')
    #
    #     words_input_layer = pnl.TransferMechanism(size=3,
    #                                               function=pnl.Linear,
    #                                               name='WORDS_INPUT')
    #
    #     task_input_layer = pnl.TransferMechanism(size=2,
    #                                              function=pnl.Linear,
    #                                              name='TASK_INPUT')
    #
    #     task_layer = pnl.RecurrentTransferMechanism(size=2,
    #                                                 function=pnl.Logistic(),
    #                                                 hetero=-2,
    #                                                 integrator_mode=True,
    #                                                 integration_rate=0.01,
    #                                                 name='TASK_LAYER')
    #
    #     colors_hidden_layer = pnl.RecurrentTransferMechanism(size=3,
    #                                                          function=pnl.Logistic(bias=4.0),
    #                                                          # bias 4.0 is -4.0 in the paper see Docs for description
    #                                                          integrator_mode=True,
    #                                                          hetero=-2,
    #                                                          integration_rate=0.01,  # cohen-huston text says 0.01
    #                                                          name='COLORS_HIDDEN')
    #
    #     words_hidden_layer = pnl.RecurrentTransferMechanism(size=3,
    #                                                         function=pnl.Logistic(bias=4.0),
    #                                                         integrator_mode=True,
    #                                                         hetero=-2,
    #                                                         integration_rate=0.01,
    #                                                         name='WORDS_HIDDEN')
    #
    #     #   Response layer, responses: ('red', 'green')
    #     response_layer = pnl.RecurrentTransferMechanism(size=2,
    #                                                     function=pnl.Logistic(),
    #                                                     hetero=-2.0,
    #                                                     integrator_mode=True,
    #                                                     integration_rate=0.01,
    #                                                     output_states=[pnl.RECURRENT_OUTPUT.RESULT,
    #                                                                    {pnl.NAME: 'DECISION_ENERGY',
    #                                                                     pnl.VARIABLE: (pnl.OWNER_VALUE, 0),
    #                                                                     pnl.FUNCTION: pnl.Stability(
    #                                                                         default_variable=np.array([0.0, 0.0]),
    #                                                                         metric=pnl.ENERGY,
    #                                                                         matrix=np.array([[0.0, -4.0],
    #                                                                                          [-4.0, 0.0]]))}],
    #                                                     name='RESPONSE', )
    #
    #     response_layer.set_log_conditions('DECISION_ENERGY')
    #
    #     color_input_weights = pnl.MappingProjection(matrix=np.array([[1.0, 0.0, 0.0],
    #                                                                  [0.0, 1.0, 0.0],
    #                                                                  [0.0, 0.0, 1.0]]))
    #
    #     word_input_weights = pnl.MappingProjection(matrix=np.array([[1.0, 0.0, 0.0],
    #                                                                 [0.0, 1.0, 0.0],
    #                                                                 [0.0, 0.0, 1.0]]))
    #
    #     task_input_weights = pnl.MappingProjection(matrix=np.array([[1.0, 0.0],
    #                                                                 [0.0, 1.0]]))
    #
    #     color_task_weights = pnl.MappingProjection(matrix=np.array([[4.0, 0.0],
    #                                                                 [4.0, 0.0],
    #                                                                 [4.0, 0.0]]))
    #
    #     task_color_weights = pnl.MappingProjection(matrix=np.array([[4.0, 4.0, 4.0],
    #                                                                 [0.0, 0.0, 0.0]]))
    #
    #     response_color_weights = pnl.MappingProjection(matrix=np.array([[1.5, 0.0, 0.0],
    #                                                                     [0.0, 1.5, 0.0]]))
    #
    #     response_word_weights = pnl.MappingProjection(matrix=np.array([[2.5, 0.0, 0.0],
    #                                                                    [0.0, 2.5, 0.0]]))
    #
    #     color_response_weights = pnl.MappingProjection(matrix=np.array([[1.5, 0.0],
    #                                                                     [0.0, 1.5],
    #                                                                     [0.0, 0.0]]))
    #
    #     word_response_weights = pnl.MappingProjection(matrix=np.array([[2.5, 0.0],
    #                                                                    [0.0, 2.5],
    #                                                                    [0.0, 0.0]]))
    #
    #     word_task_weights = pnl.MappingProjection(matrix=np.array([[0.0, 4.0],
    #                                                                [0.0, 4.0],
    #                                                                [0.0, 4.0]]))
    #
    #     task_word_weights = pnl.MappingProjection(matrix=np.array([[0.0, 0.0, 0.0],
    #                                                                [4.0, 4.0, 4.0]]))
    #
    #     # CREATE Composition
    #     comp = pnl.Composition()
    #
    #     comp.add_linear_processing_pathway([colors_input_layer,
    #                                         color_input_weights,
    #                                         colors_hidden_layer,
    #                                         color_response_weights,
    #                                         response_layer])
    #     comp.add_projection(response_color_weights, response_layer, colors_hidden_layer)
    #
    #     comp.add_linear_processing_pathway([words_input_layer,
    #                                         word_input_weights,
    #                                         words_hidden_layer,
    #                                         word_response_weights,
    #                                         response_layer])
    #     comp.add_projection(response_word_weights, response_layer, words_hidden_layer)
    #
    #     comp.add_projection(task_input_weights, task_input_layer, task_layer)
    #
    #     comp.add_projection(task_color_weights, task_layer, colors_hidden_layer)
    #     comp.add_projection(color_task_weights, colors_hidden_layer, task_layer)
    #
    #     comp.add_projection(task_word_weights, task_layer, words_hidden_layer)
    #     comp.add_projection(word_task_weights, words_hidden_layer, task_layer)
    #
    #     def trial_dict(red_color, green_color, neutral_color, red_word, green_word, neutral_word, CN, WR):
    #         trialdict = {
    #             colors_input_layer: [red_color, green_color, neutral_color],
    #             words_input_layer: [red_word, green_word, neutral_word],
    #             task_input_layer: [CN, WR]
    #         }
    #         return trialdict
    #
    #     # Define initialization trials separately
    #     CN_trial_initialize_input = trial_dict(0, 0, 0, 0, 0, 0, 1,
    #                                            0)  # red_color, green color, red_word, green word, CN, WR
    #     CN_incongruent_trial_input = trial_dict(1, 0, 0, 0, 1, 0, 1,
    #                                             0)  # red_color, green color, red_word, green word, CN, WR
    #     CN_congruent_trial_input = trial_dict(1, 0, 0, 1, 0, 0, 1,
    #                                           0)  # red_color, green color, red_word, green word, CN, WR
    #     CN_control_trial_input = trial_dict(1, 0, 0, 0, 0, 1, 1,
    #                                         0)  # red_color, green color, red_word, green word, CN, WR
    #
    #     Stimulus = [[CN_trial_initialize_input, CN_congruent_trial_input],
    #                 [CN_trial_initialize_input, CN_incongruent_trial_input],
    #                 [CN_trial_initialize_input, CN_control_trial_input]]
    #
    #     # should be 500 and 1000
    #     ntrials0 = 50
    #     ntrials = 100
    #     comp._analyze_graph()
    #
    #     def run():
    #         results = []
    #         for stim in Stimulus:
    #             # RUN the SYSTEM to initialize ----------------------------------------------------------------------------------------
    #             res = comp.run(inputs=stim[0], num_trials=ntrials0)
    #             results.append(res)
    #             res = comp.run(inputs=stim[1], num_trials=ntrials)
    #             results.append(res)
    #             # reinitialize after condition was run
    #             colors_hidden_layer.reinitialize([[0, 0, 0]])
    #             words_hidden_layer.reinitialize([[0, 0, 0]])
    #             response_layer.reinitialize([[0, 0]])
    #             task_layer.reinitialize([[0, 0]])
    #             comp.reinitialize()
    #
    #         return results
    #
    #     res = run()
    #     assert np.allclose(res[0], [0.04946301, 0.04946301, 0.03812533])
    #     assert np.allclose(res[1], [0.20351701, 0.11078586, 0.04995664])
    #     assert np.allclose(res[2], [0.04946301, 0.04946301, 0.03812533])
    #     assert np.allclose(res[3], [0.11168014, 0.20204928, 0.04996308])
    #     assert np.allclose(res[4], [0.05330691, 0.05330691, 0.03453411])
    #     assert np.allclose(res[5], [0.11327619, 0.11238362, 0.09399782])
    #
    #     if mode == 'LLVM':
    #         return
    #     r2 = response_layer.log.nparray_dictionary('DECISION_ENERGY')  # get logged DECISION_ENERGY dictionary
    #     energy = r2['DECISION_ENERGY']  # save logged DECISION_ENERGY
    #
    #     assert np.allclose(energy[:450],
    #                        [0.9907482, 0.98169891, 0.97284822, 0.96419228, 0.95572727, 0.94744946,
    #                         0.93935517, 0.93144078, 0.92370273, 0.91613752, 0.90874171, 0.90151191,
    #                         0.89444481, 0.88753715, 0.88078573, 0.8741874, 0.8677391, 0.86143779,
    #                         0.85528051, 0.84926435, 0.84338646, 0.83764405, 0.83203438, 0.82655476,
    #                         0.82120257, 0.81597521, 0.81087018, 0.805885, 0.80101724, 0.79626453,
    #                         0.79162455, 0.78709503, 0.78267373, 0.77835847, 0.77414712, 0.77003759,
    #                         0.76602783, 0.76211584, 0.75829965, 0.75457736, 0.75094707, 0.74740696,
    #                         0.74395521, 0.74059008, 0.73730983, 0.73411278, 0.73099728, 0.72796172,
    #                         0.7250045, 0.72212409, 0.71932195, 0.71660193, 0.7139626, 0.71140257,
    #                         0.70892047, 0.70651498, 0.70418478, 0.70192859, 0.69974515, 0.69763324,
    #                         0.69559166, 0.69361922, 0.69171476, 0.68987717, 0.68810533, 0.68639816,
    #                         0.68475458, 0.68317357, 0.6816541, 0.68019517, 0.67879579, 0.67745502,
    #                         0.6761719, 0.67494551, 0.67377494, 0.67265932, 0.67159776, 0.67058942,
    #                         0.66963346, 0.66872906, 0.66787541, 0.66707173, 0.66631723, 0.66561116,
    #                         0.66495278, 0.66434134, 0.66377614, 0.66325648, 0.66278164, 0.66235097,
    #                         0.66196379, 0.66161945, 0.66131731, 0.66105673, 0.66083709, 0.6606578,
    #                         0.66051824, 0.66041784, 0.66035601, 0.66033219, 0.66034583, 0.66039637,
    #                         0.66048328, 0.66060603, 0.6607641, 0.66095698, 0.66118416, 0.66144515,
    #                         0.66173948, 0.66206664, 0.66242619, 0.66281766, 0.66324058, 0.66369451,
    #                         0.66417902, 0.66469367, 0.66523802, 0.66581167, 0.66641419, 0.66704517,
    #                         0.66770422, 0.66839095, 0.66910495, 0.66984584, 0.67061326, 0.67140681,
    #                         0.67222614, 0.67307088, 0.67394067, 0.67483517, 0.67575402, 0.67669687,
    #                         0.67766339, 0.67865325, 0.67966612, 0.68070166, 0.68175955, 0.68283949,
    #                         0.68394114, 0.68506421, 0.68620839, 0.68737336, 0.68855885, 0.68976453,
    #                         0.69099013, 0.69223536, 0.69349992, 0.69478353, 0.69608592, 0.6974068,
    #                         0.9907482, 0.98169891, 0.97284822, 0.96419228, 0.95572727, 0.94744946,
    #                         0.93935517, 0.93144078, 0.92370273, 0.91613752, 0.90874171, 0.90151191,
    #                         0.89444481, 0.88753715, 0.88078573, 0.8741874, 0.8677391, 0.86143779,
    #                         0.85528051, 0.84926435, 0.84338646, 0.83764405, 0.83203438, 0.82655476,
    #                         0.82120257, 0.81597521, 0.81087018, 0.805885, 0.80101724, 0.79626453,
    #                         0.79162455, 0.78709503, 0.78267373, 0.77835847, 0.77414712, 0.77003759,
    #                         0.76602783, 0.76211584, 0.75829965, 0.75457736, 0.75094707, 0.74740696,
    #                         0.74395521, 0.74059008, 0.73730983, 0.73411278, 0.73099728, 0.72796172,
    #                         0.7250045, 0.72212409, 0.71932195, 0.71660193, 0.7139626, 0.71140257,
    #                         0.70892048, 0.70651499, 0.70418479, 0.70192861, 0.69974518, 0.69763329,
    #                         0.69559172, 0.69361931, 0.69171489, 0.68987734, 0.68810556, 0.68639845,
    #                         0.68475496, 0.68317405, 0.6816547, 0.68019591, 0.6787967, 0.67745612,
    #                         0.67617322, 0.67494709, 0.67377682, 0.67266154, 0.67160036, 0.67059245,
    #                         0.66963697, 0.6687331, 0.66788005, 0.66707703, 0.66632327, 0.66561801,
    #                         0.66496052, 0.66435007, 0.66378595, 0.66326745, 0.6627939, 0.66236463,
    #                         0.66197896, 0.66163626, 0.66133589, 0.66107724, 0.66085967, 0.66068261,
    #                         0.66054545, 0.66044762, 0.66038855, 0.66036769, 0.66038449, 0.66043841,
    #                         0.66052892, 0.66065551, 0.66081767, 0.6610149, 0.6612467, 0.6615126,
    #                         0.66181212, 0.66214479, 0.66251017, 0.6629078, 0.66333724, 0.66379805,
    #                         0.66428981, 0.66481211, 0.66536452, 0.66594665, 0.66655809, 0.66719846,
    #                         0.66786737, 0.66856444, 0.66928929, 0.67004157, 0.67082092, 0.67162697,
    #                         0.67245938, 0.67331781, 0.67420192, 0.67511137, 0.67604585, 0.67700502,
    #                         0.67798857, 0.67899619, 0.68002758, 0.68108242, 0.68216042, 0.6832613,
    #                         0.68438475, 0.68553049, 0.68669824, 0.68788774, 0.68909869, 0.69033084,
    #                         0.69158392, 0.69285767, 0.69415183, 0.69546615, 0.69680037, 0.69815425,
    #                         0.9907482, 0.98169891, 0.97284822, 0.96419228, 0.95572727, 0.94744946,
    #                         0.93935517, 0.93144078, 0.92370273, 0.91613752, 0.90874171, 0.90151191,
    #                         0.89444481, 0.88753715, 0.88078573, 0.8741874, 0.8677391, 0.86143779,
    #                         0.85528051, 0.84926435, 0.84338646, 0.83764405, 0.83203438, 0.82655476,
    #                         0.82120257, 0.81597521, 0.81087018, 0.805885, 0.80101724, 0.79626453,
    #                         0.79162455, 0.78709503, 0.78267373, 0.77835847, 0.77414712, 0.77003759,
    #                         0.76602783, 0.76211584, 0.75829965, 0.75457736, 0.75094707, 0.74740696,
    #                         0.74395521, 0.74059008, 0.73730983, 0.73411278, 0.73099728, 0.72796172,
    #                         0.7250045, 0.72212409, 0.71932195, 0.7165966, 0.71394661, 0.71137057,
    #                         0.70886708, 0.70643479, 0.70407238, 0.70177856, 0.69955206, 0.69739162,
    #                         0.69529605, 0.69326414, 0.69129474, 0.68938671, 0.68753892, 0.6857503,
    #                         0.68401976, 0.68234626, 0.68072878, 0.67916632, 0.67765789, 0.67620253,
    #                         0.67479929, 0.67344727, 0.67214554, 0.67089324, 0.66968949, 0.66853344,
    #                         0.66742427, 0.66636116, 0.66534331, 0.66436994, 0.66344028, 0.66255359,
    #                         0.66170913, 0.66090618, 0.66014404, 0.65942201, 0.65873941, 0.65809559,
    #                         0.65748989, 0.65692167, 0.6563903, 0.65589518, 0.6554357, 0.65501128,
    #                         0.65462132, 0.65426528, 0.65394258, 0.65365269, 0.65339506, 0.65316919,
    #                         0.65297454, 0.65281061, 0.65267692, 0.65257297, 0.65249828, 0.65245239,
    #                         0.65243484, 0.65244517, 0.65248294, 0.65254773, 0.65263909, 0.65275661,
    #                         0.65289989, 0.6530685, 0.65326207, 0.65348019, 0.65372249, 0.65398859,
    #                         0.65427811, 0.6545907, 0.65492599, 0.65528364, 0.6556633, 0.65606463,
    #                         0.65648729, 0.65693097, 0.65739533, 0.65788006, 0.65838485, 0.65890938,
    #                         0.65945336, 0.6600165, 0.66059849, 0.66119904, 0.66181789, 0.66245474,
    #                         0.66310932, 0.66378136, 0.6644706, 0.66517677, 0.66589961, 0.66663887,
    #                         0.66739429, 0.66816564, 0.66895265, 0.66975511, 0.67057276, 0.67140537],
    #                        atol=1e-02)


