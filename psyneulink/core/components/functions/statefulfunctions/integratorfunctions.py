#
# Princeton University licenses this file to You under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may obtain a copy of the License at:
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
#
#
# *****************************************  INTEGRATOR FUNCTIONS ******************************************************
'''

Functions that integrate current value of input with previous value.

* `IntegratorFunction`
* `ConstantIntegrator`
* `AccumulatorIntegrator`
* `SimpleIntegrator`
* `AdaptiveIntegrator`
* `DualAdaptiveIntegrator`
* `DriftDiffusionIntegrator`
* `OrnsteinUhlenbeckIntegrator`
* `InteractiveActivationIntegrator`
* `LeakyCompetingIntegrator`
* `FitzHughNagumoIntegrator`

'''

import functools
import itertools
import numbers
import warnings

import numpy as np
import typecheck as tc

from psyneulink.core import llvm as pnlvm
from psyneulink.core.components.component import DefaultsFlexibility
from psyneulink.core.components.functions.function import \
    Function_Base, FunctionError, MULTIPLICATIVE_PARAM, ADDITIVE_PARAM
from psyneulink.core.components.functions.distributionfunctions import DistributionFunction, THRESHOLD
from psyneulink.core.components.functions.statefulfunctions.statefulfunction import StatefulFunction
from psyneulink.core.globals.keywords import \
    ACCUMULATOR_INTEGRATOR_FUNCTION, ADAPTIVE_INTEGRATOR_FUNCTION, CONSTANT_INTEGRATOR_FUNCTION, DECAY, \
    DRIFT_DIFFUSION_INTEGRATOR_FUNCTION, FITZHUGHNAGUMO_INTEGRATOR_FUNCTION, FUNCTION, INCREMENT, \
    INITIALIZER, INPUT_STATES, INTERACTIVE_ACTIVATION_INTEGRATOR_FUNCTION, LEAKY_COMPETING_INTEGRATOR_FUNCTION, NOISE, \
    OFFSET, OPERATION, ORNSTEIN_UHLENBECK_INTEGRATOR_FUNCTION, OUTPUT_STATES, PRODUCT, RATE, REST, \
    SCALE, SIMPLE_INTEGRATOR_FUNCTION, SUM, \
    TIME_STEP_SIZE, DUAL_ADAPTIVE_INTEGRATOR_FUNCTION, \
    INTEGRATOR_FUNCTION, INTEGRATOR_FUNCTION_TYPE
from psyneulink.core.globals.parameters import Param
from psyneulink.core.globals.utilities import parameter_spec, all_within_range, iscompatible
from psyneulink.core.globals.context import ContextFlags
from psyneulink.core.globals.preferences.componentpreferenceset import is_pref_set


__all__ = ['SimpleIntegrator', 'ConstantIntegrator', 'AdaptiveIntegrator', 'DriftDiffusionIntegrator',
           'OrnsteinUhlenbeckIntegrator', 'FitzHughNagumoIntegrator', 'AccumulatorIntegrator',
           'LeakyCompetingIntegrator', 'DualAdaptiveIntegrator', 'InteractiveActivationIntegrator',
           'S_MINUS_L', 'L_MINUS_S'
           ]


# • why does integrator return a 2d array?
# • are rate and noise converted to 1d np.array?  If not, correct docstring
# • can noise and initializer be an array?  If so, validated in validate_param?

class IntegratorFunction(StatefulFunction):  # -------------------------------------------------------------------------
    """
    IntegratorFunction(         \
        default_variable=None,  \
        initializer,            \
        rate=1.0,               \
        noise=0.0,              \
        time_step_size=1.0,     \
        params=None,            \
        owner=None,             \
        prefs=None,             \
        )

    .. _Integrator:

    Base class for Functions that integrate current value of `variable <IntegratorFunction.variable>` with its prior
    value.  For most subclasses, `variable <IntegratorFunction.variable>` can be a single float or an array.  If it is
    an array, each element is integrated independently of the others.

    .. _IntegratorFunction_Parameter_Spec:

    .. note::
        If `variable <IntegratorFunction.variable>` is an array, for any parameter that is specified as a float its
        value is applied uniformly to all elements of the relevant term of the integral (e.g., `variable
        <IntegratorFunction.variable>` or `previous_value <IntegratorFunction.previous_value>`, depending on the
        subclass);  for any paramter specified as an array, it must be the same length as `variable
        <IntegratorFunction.variable>`, and it is applied elementwise (Hadarmard) to the relevant term of the integral.

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for the value to be integrated;  if it is a list or array, each element is independently
        integrated.

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration.  If it is a list or array, it must be the same length as
        `variable <IntegratorFunction.variable>` (see `initializer <IntegratorFunction.initializer>`
        for details).

    rate : float, list or 1d array : default 1.0
        specifies the rate of integration.  If it is a list or array, it must be the same length as
        `variable <IntegratorFunction.variable>` (see `rate <IntegratorFunction.rate>` for details).

    noise : float, function, list or 1d array : default 0.0
        specifies random value added to integral in each call to `function <IntegratorFunction.function>`;
        if it is a list or array, it must be the same length as `variable <IntegratorFunction.variable>`
        (see `noise <Integrator_Noise>` for additonal details).

    time_step_size : float : default 0.0
        determines the timing precision of the integration process

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        current input value some portion of which (determined by `rate <IntegratorFunction.rate>`) that will be
        added to the prior value;  if it is an array, each element is independently integrated.

    .. _Integrator_Rate:

    rate : float or 1d array
        determines the rate of integration. If it is a float or has a single value, it is applied to all elements
        of `variable <IntegratorFunction.variable>` and/or `previous_value <IntegrationFunction.previous_value>`
        (depending on the subclass);  if it has more than one element, each element is applied to the corresponding
        element of `variable <IntegratorFunction.variable>` and/or `previous_value <IntegratorFunction.previous_value>`.

    .. _Integrator_Noise:

    noise : float, Function or 1d array
        random value added to integral in each call to `function <Integrator.function>`. If `variable
        <Integrator.variable>` is a list or array, and noise is a float or function, it is applied
        for each element of `variable <Integrator.variable>`. If noise is a function, it is executed and applied
        separately for each element of `variable <Integrator.variable>`.  If noise is a list or array, each
        element is applied to each element of the integral corresponding that of `variable <Integrator.variable>`.

        .. hint::
            To generate random noise that varies for every execution, a probability distribution function should be
            used (see `Distribution Functions <DistributionFunction>` for details), that generates a new noise value
            from its distribution on each execution. If noise is specified as a float, a function with a fixed
            output, or a list or array of either of these, then noise is simply an offset that remains the same
            across all executions.

    .. _Integrator_Initializer:

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value(s) to which `previous_value
        <IntegratorFunction.previous_value>` is set.  If `variable <Integrator.variable>` is a list or array, and
        initializer is a float or has a single element, it is applied to each element of `previous_value
        <Integrator.previous_value>`. If initializer is a list or array, each element is applied to the corresponding
        element of `previous_value <Integrator.previous_value>`.

    previous_value : 1d array
        stores previous value with which `variable <IntegratorFunction.variable>` is integrated.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentType = INTEGRATOR_FUNCTION_TYPE
    componentName = INTEGRATOR_FUNCTION

    class Params(StatefulFunction.Params):
        """
            Attributes
            ----------

                rate
                    see `rate <IntegratorFunction.rate>`

                    :default value: 1.0
                    :type: float

                noise
                    see `noise <IntegratorFunction.noise>`

                    :default value: 0.0
                    :type: float

        """
        rate = Param(1.0, modulable=True)
        noise = Param(0.0, modulable=True)
        previous_value = np.array([0])
        initializer = np.array([0])

    paramClassDefaults = StatefulFunction.paramClassDefaults.copy()

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 rate: parameter_spec = 1.0,
                 noise=0.0,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None,
                 context=None):

      # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(params=params)

        # # does not actually get set in _assign_args_to_param_dicts but we need it as an instance_default
        # params[INITIALIZER] = initializer

        super().__init__(default_variable=default_variable,
                         initializer=initializer,
                         rate=rate,
                         noise=noise,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         context=context)

        self.has_initializers = True

    def _EWMA_filter(self, previous_value, rate, variable):
        '''Return `exponentially weighted moving average (EWMA)
        <https://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average>`_ of a variable'''
        return (1 - rate) * previous_value + rate * variable

    def _logistic(self, variable, gain, bias):
        '''Return logistic transform of variable'''
        return 1 / (1 + np.exp(-(gain * variable) + bias))

    def _euler(self, previous_value, previous_time, slope, time_step_size):

        if callable(slope):
            slope = slope(previous_time, previous_value)

        return previous_value + slope * time_step_size

    def _runge_kutta_4(self, previous_value, previous_time, slope, time_step_size):

        if callable(slope):
            slope_approx_1 = slope(previous_time,
                                   previous_value)

            slope_approx_2 = slope(previous_time + time_step_size / 2,
                                   previous_value + (0.5 * time_step_size * slope_approx_1))

            slope_approx_3 = slope(previous_time + time_step_size / 2,
                                   previous_value + (0.5 * time_step_size * slope_approx_2))

            slope_approx_4 = slope(previous_time + time_step_size,
                                   previous_value + (time_step_size * slope_approx_3))

            value = previous_value \
                    + (time_step_size / 6) * (slope_approx_1 + 2 * (slope_approx_2 + slope_approx_3) + slope_approx_4)

        else:
            value = previous_value + time_step_size * slope

        return value

    def function(self, *args, **kwargs):
        raise FunctionError("IntegratorFunction is not meant to be called explicitly")


# *********************************************** INTEGRATOR FUNCTIONS *************************************************


class ConstantIntegrator(IntegratorFunction):  # -----------------------------------------------------------------------
    """
    ConstantIntegrator(        \
        default_variable=None, \
        rate=1.0,              \
        noise=0.0,             \
        scale=1.0,             \
        offset=0.0,            \
        initializer,           \
        params=None,           \
        owner=None,            \
        prefs=None,            \
        )

    .. _ConstantIntegrator:

    `function <ConstantIntegrator.function>` returns:

    .. math::
        scale \\cdot (previous\\_value + rate  + noise) + offset

    (ignores `variable <IntegratorFunction.variable>`).

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `offset <ConstantIntegrator.offset>`
    | *ADDITIVE_PARAM:* `rate <ConstantIntegrator.rate>`
    |

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for the value to be integrated;  if it is a list or array, each element is independently
        integrated.

    rate : float, list or 1d array : default 1.0
        specifies the rate of integration;  if it is a list or array, it must be the same length as
        `variable <ConstantIntegrator.variable>` (see `rate <ConstantIntegrator.rate>` for details).

    noise : float, function, list or 1d array : default 0.0
        specifies random value to be added to integral in each call to `function <ConstantIntegrator.function>`;
        if it is a list or array, it must be the same length as `variable <ConstantIntegrator.variable>`
        (see `noise <Integrator_Noise>` for additonal details).

    scale : float, list or 1d array : default 1.0
        specifies a constant value by which integral is multiplied in each call to `function 
        <ConstantIntegrator.function>`; if it is a list or array, it must be the same length as `variable
        <ConstantIntegrator.variable>` (see `offset <ConstantIntegrator.offset>` for details).


    offset : float, list or 1d array : default 0.0
        specifies a constant value added to integral after scale is applied in each call to `function 
        <ConstantIntegrator.function>`;  if it is a list or array, it must be the same length as
        `variable <ConstantIntegrator.variable>` (see `offset <ConstantIntegrator.offset>` for details).

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration.  If it is a list or array, it must be the same length as
        `default_variable <ConstantIntegrator.variable>` (see `initializer <Integrator_Initializer>`
        for details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        **Ignored** by the ConstantIntegrator function. Use `LeakyCompetingIntegrator` or `AdaptiveIntegrator` for
        integrator functions that depend on both a prior value and a new value (variable).

    rate : float or 1d array
        determines the rate of integration. If it is a float or has a single element, its value is applied to all
        the elements of `previous_value <ConstantIntegrator.previous_value>`; if it is an array, each
        element is applied to the corresponding element of `previous_value <ConstantIntegrator.previous_value>`.
        Serves as *ADDITIVE_PARAM* for `modulation <ModulatorySignal_Modulation>` of `function
        <ConstantIntegrator.function>`.

    noise : float, Function or 1d array
        random value added to integral in each call to `function <ConstantIntegrator.function>`
        (see `noise <Integrator_Noise>` for details).

    scale : float, list or 1d array
        constant value by which integral is multiplied in each call to `function <ConstantIntegrator.function>`.
        If `variable <ConstantIntegrator.variable>` is a list or array and scale is a float, scale is applied
        to each element of the integral;  if scale is a list or array, each of its elements is applied to each of
        the corresponding elements of the integral (i.e., Hadamard multiplication).  Serves as *MULTIPLICATIVE_PARAM*
        for `modulation <ModulatorySignal_Modulation>` of `function <ConstantIntegrator.function>`.

    offset : float or 1d array
        constant value added to integral after scale is applied in each call to `function
        <ConstantIntegrator.function>`. If `variable <ConstantIntegrator.variable>` is an array and offset is a
        float, offset is applied to each element of the integral;  if offset is a list or array, each of its elements
        is applied to each of the corresponding elements of the integral (i.e., Hadamard addition).

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value(s) to which `previous_value
        <ConstantIntegrator.previous_value>` is set (see `initializer <Integrator_Initializer>` for details).

    previous_value : 1d array : default ClassDefaults.variable
        stores previous value to which `rate <ConstantIntegrator.rate>` and `noise <ConstantIntegrator.noise>` will be
        added.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = CONSTANT_INTEGRATOR_FUNCTION

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                noise
                    see `noise <ConstantIntegrator.noise>`

                    :default value: 0.0
                    :type: float

                offset
                    see `offset <ConstantIntegrator.offset>`

                    :default value: 0.0
                    :type: float

                rate
                    see `rate <ConstantIntegrator.rate>`

                    :default value: 0.0
                    :type: float

                scale
                    see `scale <ConstantIntegrator.scale>`

                    :default value: 1.0
                    :type: float

        """
        rate = Param(0.0, modulable=True, aliases=[ADDITIVE_PARAM])
        noise = Param(0.0, modulable=True)
        scale = Param(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        offset = Param(0.0, modulable=True)

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        RATE: None,
        NOISE: None,
        SCALE: None,
        OFFSET: None,
    })

    multiplicative_param = SCALE
    additive_param = RATE

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 # rate: parameter_spec = 1.0,
                 rate=0.0,
                 noise=0.0,
                 scale=1.0,
                 offset=0.0,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None):

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(rate=rate,
                                                  noise=noise,
                                                  scale=scale,
                                                  offset=offset,
                                                  initializer=initializer,
                                                  params=params)

        # Assign here as default, for use in initialization of function
        self.previous_value = initializer

        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        # Reassign to initializer in case default value was overridden

        self.has_initializers = True

    def _validate_rate(self, rate):
        # unlike other Integrators, variable does not need to match rate

        if isinstance(rate, list):
            rate = np.asarray(rate)

        rate_type_msg = 'The rate parameter of {0} must be a number or an array/list of at most 1d (you gave: {1})'
        if isinstance(rate, np.ndarray):
            # kmantel: current test_gating test depends on 2d rate
            #   this should be looked at but for now this restriction is removed
            # if rate.ndim > 1:
            #     raise FunctionError(rate_type_msg.format(self.name, rate))
            pass
        elif not isinstance(rate, numbers.Number):
            raise FunctionError(rate_type_msg.format(self.name, rate))

        if self._default_variable_flexibility is DefaultsFlexibility.FLEXIBLE:
            self.instance_defaults.variable = np.zeros_like(np.array(rate))
            self._instantiate_value()
            self._default_variable_flexibility = DefaultsFlexibility.INCREASE_DIMENSION

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """

        Arguments
        ---------

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.

        Returns
        -------

        updated value of integral : 2d array

        """
        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)

        rate = np.array(self.rate).astype(float)
        offset = self.get_current_function_param(OFFSET, execution_id)
        scale = self.get_current_function_param(SCALE, execution_id)
        noise = self._try_execute_param(self.noise, variable)

        previous_value = np.atleast_2d(self.get_previous_value(execution_id))

        value = previous_value + rate + noise

        adjusted_value = value * scale + offset

        # If this NOT an initialization run, update the old value
        # If it IS an initialization run, leave as is
        #    (don't want to count it as an execution step)
        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            self.parameters.previous_value.set(adjusted_value, execution_id)
        return self.convert_output_type(adjusted_value)


class AccumulatorIntegrator(IntegratorFunction):  # --------------------------------------------------------------------
    """
    AccumulatorIntegrator(              \
        default_variable=None,          \
        rate=1.0,                       \
        increment=0.0,                  \
        noise=0.0,                      \
        initializer,                    \
        params=None,                    \
        owner=None,                     \
        prefs=None,                     \
        )

    .. _AccumulatorIntegrator:

    `function <AccumulatorIntegrator.function>` returns:

    .. math::
        previous_value * rate + increment  + noise

    (ignores `variable <IntegratorFunction.variable>`).

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `rate <AccumulatorIntegrator.rate>`
    | *ADDITIVE_PARAM:* `increment <AccumulatorIntegrator.increment>`
    |

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for the value to be integrated;  if it is a list or array, each element is independently
        integrated.

    rate : float, list or 1d array : default 1.0
        specifies the rate of decay;  if it is a list or array, it must be the same length as `variable
        <AccumulatorIntegrator.variable>` (see `rate <AccumulatorIntegrator.rate>` for additional details.

    increment : float, list or 1d array : default 0.0
        specifies an amount to be added to `previous_value <AccumulatorIntegrator.previous_value>` in each call to
        `function <AccumulatorIntegrator.function>` (see `increment <AccumulatorIntegrator.increment>` for details).
        If it is a list or array, it must be the same length as `variable <AccumulatorIntegrator.variable>`
        (see `increment <AccumulatorIntegrator.increment>` for details).

    noise : float, Function, list or 1d array : default 0.0
        specifies random value added to `prevous_value <AccumulatorIntegrator.previous_value>` in each call to
        `function <AccumulatorIntegrator.function>`; if it is a list or array, it must be the same length as
        `variable <AccumulatorIntegrator.variable>` (see `noise <Integrator_Noise>` for additonal details).

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration.  If it is a list or array, it must be the same length as
        `default_variable <AccumulatorIntegrator.variable>` (see `initializer
        <AccumulatorIntegrator.initializer>` for details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        **Ignored** by the AccumulatorIntegrator function. Use `LeakyCompetingIntegrator` or `AdaptiveIntegrator` for
        integrator functions that depend on both a prior value and a new value (variable).

    rate : float or 1d array
        determines the rate of exponential decay of `previous_value <AccumulatorIntegrator.previous_value>` in each
        call to `function <AccumulatorIntegrator.function>`. If it is a float or has a single element, its value is
        applied to all the elements of `previous_value <AccumulatorIntegrator.previous_value>`; if it is an array, each
        element is applied to the corresponding element of `previous_value <AccumulatorIntegrator.previous_value>`.
        Serves as *MULTIPLICATIVE_PARAM* for `modulation <ModulatorySignal_Modulation>` of `function
        <AccumulatorIntegrator.function>`.

    increment : float, function, or 1d array
        determines the amount added to `previous_value <AccumulatorIntegrator.previous_value>` in each call to
        `function <AccumulatorIntegrator.function>`.  If it is a list or array, it must be the same length as
        `variable <AccumulatorIntegrator.variable>` and each element is added to the corresponding element of
        `previous_value <AccumulatorIntegrator.previous_value>` (i.e., it is used for Hadamard addition).  If it is a
        scalar or has a single element, its value is added to all the elements of `previous_value
        <AccumulatorIntegrator.previous_value>`.  Serves as *ADDITIVE_PARAM* for
        `modulation <ModulatorySignal_Modulation>` of `function <AccumulatorIntegrator.function>`.

    noise : float, Function or 1d array
        random value added in each call to `function <AccumulatorIntegrator.function>`
        (see `noise <Integrator_Noise>` for details).

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value(s) to which `previous_value
        <AccumulatorIntegrator.previous_value>` is set (see `initializer <Integrator_Initializer>` for details).

    previous_value : 1d array : default ClassDefaults.variable
        stores previous value to which `rate <AccumulatorIntegrator.rate>` and `noise <AccumulatorIntegrator.noise>`
        will be added.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = ACCUMULATOR_INTEGRATOR_FUNCTION

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                increment
                    see `increment <AccumulatorIntegrator.increment>`

                    :default value: None
                    :type:

                rate
                    see `rate <AccumulatorIntegrator.rate>`

                    :default value: None
                    :type:

        """
        rate = Param(None, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        increment = Param(None, modulable=True, aliases=[ADDITIVE_PARAM])

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        RATE: None,
        INCREMENT: None,
        NOISE: None,
    })

    # multiplicative param does not make sense in this case
    multiplicative_param = RATE
    additive_param = INCREMENT

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 rate=None,
                 increment=None,
                 noise=0.0,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None):

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(rate=rate,
                                                  increment=increment,
                                                  noise=noise,
                                                  initializer=initializer,
                                                  params=params)

        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        self.has_initializers = True

    def _accumulator_check_args(self, variable=None, execution_id=None, params=None, target_set=None, context=None):
        """validate params and assign any runtime params.

        Called by AccumulatorIntegrator to validate params
        Validation can be suppressed by turning parameter_validation attribute off
        target_set is a params dictionary to which params should be assigned;
           otherwise, they are assigned to paramsCurrent;

        Does the following:
        - assign runtime params to paramsCurrent
        - validate params if PARAM_VALIDATION is set

        :param params: (dict) - params to validate
        :target_set: (dict) - set to which params should be assigned (default: self.paramsCurrent)
        :return:
        """

        # PARAMS ------------------------------------------------------------

        # If target_set is not specified, use paramsCurrent
        if target_set is None:
            target_set = self.paramsCurrent

        # # MODIFIED 11/27/16 OLD:
        # # If parameter_validation is set, the function was called with params,
        # #   and they have changed, then validate requested values and assign to target_set
        # if self.prefs.paramValidationPref and params and not params is None and not params is target_set:
        #     # self._validate_params(params, target_set, context=FUNCTION_CHECK_ARGS)
        #     self._validate_params(request_set=params, target_set=target_set, context=context)

        # If params have been passed, treat as runtime params and assign to paramsCurrent
        #   (relabel params as runtime_params for clarity)
        if execution_id in self._runtime_params_reset:
            for key in self._runtime_params_reset[execution_id]:
                self._set_parameter_value(key, self._runtime_params_reset[execution_id][key], execution_id)
        self._runtime_params_reset[execution_id] = {}

        runtime_params = params
        if runtime_params:
            for param_name in runtime_params:
                if hasattr(self, param_name):
                    if param_name in {FUNCTION, INPUT_STATES, OUTPUT_STATES}:
                        continue
                    if execution_id not in self._runtime_params_reset:
                        self._runtime_params_reset[execution_id] = {}
                    self._runtime_params_reset[execution_id][param_name] = getattr(self.parameters, param_name).get(execution_id)
                    self._set_parameter_value(param_name, runtime_params[param_name], execution_id)

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """

        Arguments
        ---------

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.


        Returns
        -------

        updated value of integral : 2d array

        """
        self._accumulator_check_args(variable, execution_id=execution_id, params=params, context=context)

        rate = self.get_current_function_param(RATE, execution_id)
        increment = self.get_current_function_param(INCREMENT, execution_id)
        noise = self._try_execute_param(self.get_current_function_param(NOISE, execution_id), variable)

        if rate is None:
            rate = 1.0

        if increment is None:
            increment = 0.0

        previous_value = np.atleast_2d(self.get_previous_value(execution_id))

        value = previous_value * rate + noise + increment

        # If this NOT an initialization run, update the old value
        # If it IS an initialization run, leave as is
        #    (don't want to count it as an execution step)
        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            self.parameters.previous_value.set(value, execution_id, override=True)

        return self.convert_output_type(value)


class SimpleIntegrator(IntegratorFunction):  # -------------------------------------------------------------------------
    """
    SimpleIntegrator(           \
        default_variable=None,  \
        rate=1.0,               \
        noise=0.0,              \
        offset=0.0,             \
        initializer,            \
        params=None,            \
        owner=None,             \
        prefs=None,             \
        )

    .. _SimpleIntegrator:

    `function <SimpleIntegrator.function>` returns:

    .. math::

        previous_value + rate * variable + noise + offset

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `rate <SimpleIntegrator.rate>`
    | *ADDITIVE_PARAM:* `offset <SimpleIntegrator.offset>`
    |

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for the value to be integrated;  if it is a list or array, each element is independently
        integrated.

    rate : float, list or 1d array : default 1.0
        specifies the rate of integration;  if it is a list or array, it must be the same length as
        `variable <SimpleIntegrator.variable>` (see `rate <SimpleIntegrator.rate>` for details).

    noise : float, function, list or 1d array : default 0.0
        specifies random value added to integral in each call to `function <SimpleIntegrator.function>`;
        if it is a list or array, it must be the same length as `variable <SimpleIntegrator.variable>`
        (see `noise <Integrator_Noise>` for details).

    offset : float, list or 1d array : default 0.0
        specifies constant value added to integral in each call to `function <SimpleIntegrator.function>`;
        if it is a list or array, it must be the same length as `variable <SimpleIntegrator.variable>`
        (see `offset <SimpleIntegrator.offset>` for details).

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration;  if it is a list or array, it must be the same length as
        `default_variable <SimpleIntegrator.variable>` (see `initializer <Integrator_Initializer>`
        for details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        current input value some portion of which (determined by `rate <SimpleIntegrator.rate>`) will be
        added to the prior value;  if it is an array, each element is independently integrated.

    rate : float or 1d array
        determines the rate of integration. If it is a float or has a single element, it is applied
        to all elements of `variable <SimpleIntegrator.variable>`;  if it has more than one element, each element
        is applied to the corresponding element of `variable <SimpleIntegrator.variable>`.  Serves as
        *MULTIPLICATIVE_PARAM* for `modulation <ModulatorySignal_Modulation>` of `function <SimpleIntegrator.function>`.

    noise : float, Function or 1d array
        random value added to integral in each call to `function <SimpleIntegrator.function>`
        (see `noise <Integrator_Noise>` for details).

    offset : float or 1d array
        constant value added to integral in each call to `function <SimpleIntegrator.function>`. If `variable
        <SimpleIntegrator.variable>` is an array and offset is a float, offset is applied to each element of the
        integral;  if offset is a list or array, each of its elements is applied to each of the corresponding
        elements of the integral (i.e., Hadamard addition). Serves as *ADDITIVE_PARAM* for `modulation
        <ModulatorySignal_Modulation>` of `function <SimpleIntegrator.function>`.

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value to which `previous_value
        <SimpleIntegrator.previous_value>` is set (see `initializer <Integrator_Initializer>` for details).

    previous_value : 1d array : default ClassDefaults.variable
        stores previous value with which `variable <SimpleIntegrator.variable>` is integrated.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = SIMPLE_INTEGRATOR_FUNCTION

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        RATE: None,
        NOISE: None,
        OFFSET: None
    })

    multiplicative_param = RATE
    additive_param = OFFSET

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                offset
                    see `offset <SimpleIntegrator.offset>`

                    :default value: 0.0
                    :type: float

                rate
                    see `rate <SimpleIntegrator.rate>`

                    :default value: 1.0
                    :type: float

        """
        rate = Param(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        offset = Param(0.0, modulable=True, aliases=[ADDITIVE_PARAM])

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 rate: parameter_spec = 1.0,
                 noise=0.0,
                 offset=None,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None):

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(rate=rate,
                                                  noise=noise,
                                                  offset=offset,
                                                  initializer=initializer,
                                                  params=params)
        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        self.has_initializers = True

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """
        Arguments
        ---------

        variable : number, list or array : default ClassDefaults.variable
           a single value or array of values to be integrated.

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.

        Returns
        -------

        updated value of integral : 2d array

        """

        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)

        rate = np.array(self.get_current_function_param(RATE, execution_id)).astype(float)

        offset = self.get_current_function_param(OFFSET, execution_id)
        if offset is None:
            offset = 0.0

        # execute noise if it is a function
        noise = self._try_execute_param(self.get_current_function_param(NOISE, execution_id), variable)
        previous_value = self.get_previous_value(execution_id)
        new_value = variable

        value = previous_value + (new_value * rate) + noise

        adjusted_value = value + offset

        # If this NOT an initialization run, update the old value
        # If it IS an initialization run, leave as is
        #    (don't want to count it as an execution step)
        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            self.parameters.previous_value.set(adjusted_value, execution_id)

        return self.convert_output_type(adjusted_value)


class AdaptiveIntegrator(IntegratorFunction):  # -----------------------------------------------------------------------
    """
    AdaptiveIntegrator(         \
        default_variable=None,  \
        rate=1.0,               \
        noise=0.0,              \
        offset=0.0,             \
        initializer,            \
        params=None,            \
        owner=None,             \
        prefs=None,             \
        )

    .. _AdaptiveIntegrator:

    `function <AdapativeIntegrator.function>` returns `exponentially weighted moving average (EWMA)
    <https://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average>`_ of input:

    .. math::
        ((1-rate) * previous_value) + (rate * variable)  + noise + offset

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `rate <AdaptiveIntegrator.rate>`
    | *ADDITIVE_PARAM:* `offset <AdaptiveIntegrator.offset>`
    |

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for the value to be integrated;  if it is a list or array, each element is independently
        integrated.

    rate : float, list or 1d array : default 1.0
        specifies the smoothing factor of the `EWMA <AdaptiveIntegrator>`.  If it is a list or array, it must be the
        same length as `variable <AdaptiveIntegrator.variable>` (see `rate <AdaptiveIntegrator.rate>` for
        details).

    noise : float, function, list or 1d array : default 0.0
        specifies random value added to integral in each call to `function <AdaptiveIntegrator.function>`;
        if it is a list or array, it must be the same length as `variable <AdaptiveIntegrator.variable>`
        (see `noise <Integrator_Noise>` for details).

    offset : float, list or 1d array : default 0.0
        specifies constant value added to integral in each call to `function <AdaptiveIntegrator.function>`;  
        if it is a list or array, it must be the same length as `variable <AdaptiveIntegrator.variable>`
        (see `offset <AdaptiveIntegrator.offset>` for details).

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration.  If it is a list or array, it must be the same length as
        `default_variable <AdaptiveIntegrator.variable>` (see `initializer <Integrator_Initializer>`
        for details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        current input value some portion of which (determined by `rate <AdaptiveIntegrator.rate>`) will be
        added to the prior value;  if it is an array, each element is independently integrated.

    rate : float or 1d array
        determines the smoothing factor of the `EWMA <AdaptiveIntegrator>`. All rate elements must be between 0 and 1
        (rate = 0 --> no change, `variable <AdaptiveAdaptiveIntegrator.variable>` is ignored; rate = 1 -->
        `previous_value <AdaptiveIntegrator.previous_value>` is ignored).  If rate is a float or has a single element,
        its value is applied to all elements of `variable <AdaptiveAdaptiveIntegrator.variable>` and `previous_value
        <AdaptiveIntegrator.previous_value>`; if it is an array, each element is applied to the corresponding element
        of `variable <AdaptiveIntegrator.variable>` and `previous_value <AdaptiveIntegrator.previous_value>`).
        Serves as *MULTIPLICATIVE_PARAM*  for `modulation <ModulatorySignal_Modulation>` of `function
        <AdaptiveIntegrator.function>`.

    noise : float, Function or 1d array
        random value added to integral in each call to `function <AdaptiveIntegrator.function>`
        (see `noise <Integrator_Noise>` for details).

    offset : float or 1d array
        constant value added to integral in each call to `function <AdaptiveIntegrator.function>`.
        If `variable <AdaptiveIntegrator.variable>` is a list or array and offset is a float, offset is applied
        to each element of the integral;  if offset is a list or array, each of its elements is applied to each of
        the corresponding elements of the integral (i.e., Hadamard addition). Serves as *ADDITIVE_PARAM* for
        `modulation <ModulatorySignal_Modulation>` of `function <AdaptiveIntegrator.function>`.

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value(s) to which `previous_value
        <AdaptiveIntegrator.previous_value>` is set (see `initializer <Integrator_Initializer>` for details).

    previous_value : 1d array : default ClassDefaults.variable
        stores previous value with which `variable <AdaptiveIntegrator.variable>` is integrated.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = ADAPTIVE_INTEGRATOR_FUNCTION

    multiplicative_param = RATE
    additive_param = OFFSET

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        RATE: None,
        NOISE: None,
        OFFSET: None
    })

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                offset
                    see `offset <AdaptiveIntegrator.offset>`

                    :default value: 0.0
                    :type: float

                rate
                    see `rate <AdaptiveIntegrator.rate>`

                    :default value: 1.0
                    :type: float

        """
        rate = Param(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        offset = Param(0.0, modulable=True, aliases=[ADDITIVE_PARAM])

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 rate=1.0,
                 noise=0.0,
                 offset=0.0,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None):

        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(rate=rate,
                                                  noise=noise,
                                                  offset=offset,
                                                  initializer=initializer,
                                                  params=params)

        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        self.has_initializers = True

    def _validate_params(self, request_set, target_set=None, context=None):

        # Handle list or array for rate specification
        if RATE in request_set:
            rate = request_set[RATE]
            if isinstance(rate, (list, np.ndarray)):
                if len(rate) != 1 and len(rate) != np.array(self.instance_defaults.variable).size:
                    # If the variable was not specified, then reformat it to match rate specification
                    #    and assign ClassDefaults.variable accordingly
                    # Note: this situation can arise when the rate is parametrized (e.g., as an array) in the
                    #       AdaptiveIntegrator's constructor, where that is used as a specification for a function
                    #       parameter (e.g., for an IntegratorMechanism), whereas the input is specified as part of the
                    #       object to which the function parameter belongs (e.g., the IntegratorMechanism);
                    #       in that case, the IntegratorFunction gets instantiated using its ClassDefaults.variable ([[0]])
                    #       before the object itself, thus does not see the array specification for the input.
                    if self._default_variable_flexibility is DefaultsFlexibility.FLEXIBLE:
                        self._instantiate_defaults(variable=np.zeros_like(np.array(rate)), context=context)
                        if self.verbosePref:
                            warnings.warn(
                                "The length ({}) of the array specified for the {} parameter ({}) of {} "
                                "must match the length ({}) of the default input ({});  "
                                "the default input has been updated to match".
                                    format(len(rate), repr(RATE), rate, self.name,
                                    np.array(self.instance_defaults.variable).size, self.instance_defaults.variable))
                    else:
                        raise FunctionError(
                            "The length ({}) of the array specified for the rate parameter ({}) of {} "
                            "must match the length ({}) of the default input ({})".format(
                                len(rate),
                                rate,
                                self.name,
                                np.array(self.instance_defaults.variable).size,
                                self.instance_defaults.variable,
                            )
                        )
                        # OLD:
                        # self.paramClassDefaults[RATE] = np.zeros_like(np.array(rate))

                        # KAM changed 5/15 b/c paramClassDefaults were being updated and *requiring* future integrator
                        # function to have a rate parameter of type ndarray/list

        super()._validate_params(request_set=request_set,
                                 target_set=target_set,
                                 context=context)


        # FIX: 12/9/18 [JDC] REPLACE WITH USE OF all_within_range
        if RATE in target_set:
            # cannot use _validate_rate here because it assumes it's being run after instantiation of the object
            rate_value_msg = "The rate parameter ({}) (or all of its elements) of {} " \
                             "must be between 0.0 and 1.0 because it is an AdaptiveIntegrator"

            if isinstance(rate, np.ndarray) and rate.ndim > 0:
                for r in rate:
                    if r < 0.0 or r > 1.0:
                        raise FunctionError(rate_value_msg.format(rate, self.name))
            else:
                if rate < 0.0 or rate > 1.0:
                    raise FunctionError(rate_value_msg.format(rate, self.name))

        if NOISE in target_set:
            noise = target_set[NOISE]
            if isinstance(noise, DistributionFunction):
                noise.owner = self
                target_set[NOISE] = noise._execute
            self._validate_noise(target_set[NOISE])
            # if INITIALIZER in target_set:
            #     self._validate_initializer(target_set[INITIALIZER])

    def _validate_rate(self, rate):
        super()._validate_rate(rate)

        if isinstance(rate, list):
            rate = np.asarray(rate)

        rate_value_msg = "The rate parameter ({}) (or all of its elements) of {} " \
                         "must be between 0.0 and 1.0 because it is an AdaptiveIntegrator"

        if not all_within_range(rate, 0, 1):
            raise FunctionError(rate_value_msg.format(rate, self.name))

    def __gen_llvm_integrate(self, builder, index, ctx, vi, vo, params, state):
        rate_p, builder = ctx.get_param_ptr(self, builder, params, RATE)
        offset_p, builder = ctx.get_param_ptr(self, builder, params, OFFSET)
        noise_p, builder = ctx.get_param_ptr(self, builder, params, NOISE)

        offset = pnlvm.helpers.load_extract_scalar_array_one(builder, offset_p)

        if isinstance(rate_p.type.pointee, pnlvm.ir.ArrayType) and rate_p.type.pointee.count > 1:
            rate_p = builder.gep(rate_p, [ctx.int32_ty(0), index])
        rate = pnlvm.helpers.load_extract_scalar_array_one(builder, rate_p)

        if isinstance(noise_p.type.pointee, pnlvm.ir.ArrayType) and noise_p.type.pointee.count > 1:
            noise_p = builder.gep(noise_p, [ctx.int32_ty(0), index])
        noise = pnlvm.helpers.load_extract_scalar_array_one(builder, noise_p)

        # Get the only context member -- previous value
        prev_ptr = builder.gep(state, [ctx.int32_ty(0), ctx.int32_ty(0)])
        # Get rid of 2d array. When part of a Mechanism the input,
        # (and output, and context) are 2d arrays.
        prev_ptr = ctx.unwrap_2d_array(builder, prev_ptr)
        assert len(prev_ptr.type.pointee) == len(vi.type.pointee)

        prev_ptr = builder.gep(prev_ptr, [ctx.int32_ty(0), index])
        prev_val = builder.load(prev_ptr)

        vi_ptr = builder.gep(vi, [ctx.int32_ty(0), index])
        vi_val = builder.load(vi_ptr)

        rev_rate = builder.fsub(ctx.float_ty(1), rate)
        old_val = builder.fmul(prev_val, rev_rate)
        new_val = builder.fmul(vi_val, rate)

        ret = builder.fadd(old_val, new_val)
        ret = builder.fadd(ret, noise)
        res = builder.fadd(ret, offset)

        vo_ptr = builder.gep(vo, [ctx.int32_ty(0), index])
        builder.store(res, vo_ptr)
        builder.store(res, prev_ptr)

    def _gen_llvm_function_body(self, ctx, builder, params, context, arg_in, arg_out):
        # Get rid of 2d array.
        # When part of a Mechanism the input, and output are 2d arrays.
        arg_in = ctx.unwrap_2d_array(builder, arg_in)
        arg_out = ctx.unwrap_2d_array(builder, arg_out)

        kwargs = {"ctx": ctx, "vi": arg_in, "vo": arg_out, "params": params, "state": context}
        inner = functools.partial(self.__gen_llvm_integrate, **kwargs)
        with pnlvm.helpers.array_ptr_loop(builder, arg_in, "integrate") as args:
            inner(*args)

        return builder

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """

        Arguments
        ---------

        variable : number, list or array : default ClassDefaults.variable
           a single value or array of values to be integrated.

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.


        Returns
        -------

        updated value of integral : 2d array

        """
        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)

        rate = np.array(self.get_current_function_param(RATE, execution_id)).astype(float)
        offset = self.get_current_function_param(OFFSET, execution_id)
        # execute noise if it is a function
        noise = self._try_execute_param(self.get_current_function_param(NOISE, execution_id), variable)

        previous_value = np.atleast_2d(self.get_previous_value(execution_id))

        value = self._EWMA_filter(previous_value, rate, variable) + noise

        adjusted_value = value + offset

        # If this NOT an initialization run, update the old value
        # If it IS an initialization run, leave as is
        #    (don't want to count it as an execution step)
        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            self.parameters.previous_value.set(adjusted_value, execution_id)

        return self.convert_output_type(adjusted_value)

S_MINUS_L = 's-l'
L_MINUS_S = 'l-s'
OPERATIONS = {PRODUCT, SUM, S_MINUS_L, L_MINUS_S}


class DualAdaptiveIntegrator(IntegratorFunction):  # ------------------------------------------------------------------
    """
    DualAdaptiveIntegrator(         \
        default_variable=None,       \
        initializer=None,            \
        initial_short_term_avg=0.0,  \
        initial_long_term_avg=0.0,   \
        short_term_gain=1.0,         \
        long_term_gain=1.0,          \
        short_term_bias=0.0,         \
        long_term_bias=0.0,          \
        short_term_rate=1.0,         \
        long_term_rate=1.0,          \
        operation=PRODUCT,           \
        offset=0.0,                  \
        params=None,                 \
        owner=None,                  \
        prefs=None,                  \
        )

    .. _DualAdaptiveIntegrator:

    Combines two `exponentially weighted moving averages (EWMA)
    <https://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average>`_ of its input, each with a different
    rate, as implemented in `Aston-Jones & Cohen (2005)
    <https://www.annualreviews.org/doi/abs/10.1146/annurev.neuro.28.061604.135709>`_ to integrate utility over two
    time scales.

    `function <DualAdaptiveIntegrator.function>` computes the EWMA of `variable <DualAdaptiveIntegrator.variable>`
    using two integration rates (`short_term_rate <DualAdaptiveIntegrator.short_term_rate>` and `long_term_rate
    <DualAdaptiveIntegrator.long_term_rate>), transforms each using a logistic function, and then combines them,
    as follows:

    * **short time scale integral**:

      .. math::
         short\\_term\\_avg = short\\_term\\_rate \\cdot variable + (1 - short\\_term\\_rate) \\cdot
         previous\\_short\\_term\\_avg

    * **long time scale integral**:

      .. math::
         long\\_term\\_avg = long\\_term\\_rate \\cdot variable + (1 - long\\_term\\_rate) \\cdot
         previous\\_long\\_term\\_avg

    .. _DualAdaptive_Combined:

    * **combined integral**:

      .. math::
         value = operation(1-\\frac{1}{1+e^{short\\_term\\_gain\\ \\cdot\\ short\\_term\\_avg\\ +\\
         short\\_term\\_bias}},\\
         \\frac{1}{1+e^{long\\_term\\_gain\\ \\cdot\\ long\\_term\\_avg + long\\_term\\_bias}})\\ +\\ offset

      where *operation* is the arithmetic `operation <DualAdaptiveIntegrator.operation>` used to combine the terms.


    *Modulatory Parameters:*

    | *ADDITIVE_PARAM:* `offset <AdaptiveIntegrator.offset>`
    |

    Arguments
    ---------

    COMMENT:
    noise : float, function, list or 1d array : default 0.0
        TBI?
    COMMENT

    initial_short_term_avg : float : default 0.0
        specifies starting value for integration of short_term_avg

    initial_long_term_avg : float : default 0.0
        specifies starting value for integration of long_term_avg

    short_term_gain : float : default 1.0
        specifies gain for logistic function applied to short_term_avg

    long_term_gain : float : default 1.0
        specifies gain for logistic function applied to long_term_avg

    short_term_bias : float : default 0.0
        specifies bias for logistic function applied to short_term_avg

    long_term_bias : float : default 0.0
        specifies bias for logistic function applied to long_term_avg

    short_term_rate : float : default 1.0
        specifies smoothing factor of `EWMA <DualAdaptiveIntegrator>` filter applied to short_term_avg

    long_term_rate : float : default 1.0
        specifies smoothing factor of `EWMA <DualAdaptiveIntegrator>` filter applied to long_term_avg

    COMMENT:
    rate : float or 1d array
        determines weight assigned to `short_term_logistic and long_term_logistic <DualAdaptive_Combined>` when combined
        by `operation <DualAdaptiveIntegrator.operation>` (see `rate <DualAdaptiveIntegrator.rate>` for details.
    COMMENT

    operation : PRODUCT, SUM, S_MINUS_L or L_MINUS_S : default PRODUCT
        specifies the arithmetic operation used to combine the logistics of the short_term_avg and long_term_avg
        (see `operation <DualAdaptiveIntegrator.operation>` for details).

    offset : float or 1d array
        constant value added to integral in each call to `function <DualAdaptiveIntegrator.function>` after logistics
        of short_term_avg and long_term_avg are combined; if it is a list or array, it must be the same length as
        `variable <DualAdaptiveIntegrator.variable>` (see `offset <DualAdaptiveIntegrator.offset>` for details.

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        current input value used to compute both the short term and long term `EWMA <DualAdaptiveIntegrator>` averages.

    COMMENT:
    noise : float, Function or 1d array : default 0.0
        TBI?
    COMMENT

    initial_short_term_avg : float
        determines starting value for integration of short_term_avg

    initial_long_term_avg : float
        determines starting value for integration of long_term_avg

    short_term_gain : float
        determines gain for logistic function applied to short_term_avg

    long_term_gain : float
        determines gain for logistic function applied to long_term_avg

    short_term_bias : float
        determines bias for logistic function applied to short_term_avg

    long_term_bias : float
        determines bias for logistic function applied to long_term_avg

    short_term_rate : float
        determines smoothing factor of `EWMA <DualAdaptiveIntegrator>` filter applied to short_term_avg

    long_term_rate : float
        determines smoothing factor of `EWMA <DualAdaptiveIntegrator>` filter applied to long_term_avg

    operation : str
        determines the arithmetic operation used to combine `short_term_logistic and long_term_logistic
        <DualAdaptive_Combined>`:

        * *PRODUCT* = (1 - short_term_logistic) * long_term_logistic
        * *SUM* = (1 - short_term_logistic) + long_term_logistic
        * *S_MINUS_L* = (1 - short_term_logistic) - long_term_logistic
        * *L_MINUS_S* = long_term_logistic - (1 - short_term_logistic)

    COMMENT:
    rate : float or 1d array with element(s) in interval [0,1]: default 0.5
        determines the linearly-weighted contribution of `short_term_logistic and long_term_logistic
        <DualAdaptive_Combined>` to the integral.  For rate=0.5, each receives and equal weight of 1;  for rate<0.5,
        short_term_avg diminishes linearly to 0 while long_term_avg remains at 1;  for rate>0.5, long_term_avg
        diminishes linearly to 0 wile short_term_avg remains at 1.  If it is a float or has a single element,
        its value is applied to all the elements of short_term_logistic and long_term_logistic; if it is an array,
        each element is applied to the corresponding elements of each logistic. Serves as *MULTIPLICATIVE_PARAM*
        for `modulation <ModulatorySignal_Modulation>` of `function <DualAdaptiveIntegrator.function>`.
    COMMENT

    offset : float or 1d array
        constant value added to integral in each call to `function <DualAdaptiveIntegrator.function>` after logistics
        of short_term_avg and long_term_avg are combined. If `variable <DualAdaptiveIntegrator.variable>` is an array
        and offset is a float, offset is applied to each element of the integral;  if offset is a list or array, each
        of its elements is applied to each of the corresponding elements of the integral (i.e., Hadamard addition).
        Serves as *ADDITIVE_PARAM* for `modulation <ModulatorySignal_Modulation>` of `function
        <DualAdaptiveIntegrator.function>`.

    previous_short_term_avg : 1d array
        stores previous value with which `variable <DualAdaptiveIntegrator.variable>` is integrated using the
        `EWMA <DualAdaptiveIntegrator>` filter and short term parameters

    previous_long_term_avg : 1d array
        stores previous value with which `variable <DualAdaptiveIntegrator.variable>` is integrated using the
        `EWMA <DualAdaptiveIntegrator>` filter and long term parameters

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = DUAL_ADAPTIVE_INTEGRATOR_FUNCTION

    # multiplicative_param = RATE
    additive_param = OFFSET

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                initial_long_term_avg
                    see `initial_long_term_avg <DualAdaptiveIntegrator.initial_long_term_avg>`

                    :default value: 0.0
                    :type: float

                initial_short_term_avg
                    see `initial_short_term_avg <DualAdaptiveIntegrator.initial_short_term_avg>`

                    :default value: 0.0
                    :type: float

                long_term_bias
                    see `long_term_bias <DualAdaptiveIntegrator.long_term_bias>`

                    :default value: 0.0
                    :type: float

                long_term_gain
                    see `long_term_gain <DualAdaptiveIntegrator.long_term_gain>`

                    :default value: 1.0
                    :type: float

                long_term_logistic
                    see `long_term_logistic <DualAdaptiveIntegrator.long_term_logistic>`

                    :default value: None
                    :type:

                long_term_rate
                    see `long_term_rate <DualAdaptiveIntegrator.long_term_rate>`

                    :default value: 0.1
                    :type: float

                offset
                    see `offset <DualAdaptiveIntegrator.offset>`

                    :default value: 0.0
                    :type: float

                operation
                    see `operation <DualAdaptiveIntegrator.operation>`

                    :default value: `PRODUCT`
                    :type: str

                previous_long_term_avg
                    see `previous_long_term_avg <DualAdaptiveIntegrator.previous_long_term_avg>`

                    :default value: None
                    :type:

                previous_short_term_avg
                    see `previous_short_term_avg <DualAdaptiveIntegrator.previous_short_term_avg>`

                    :default value: None
                    :type:

                rate
                    see `rate <DualAdaptiveIntegrator.rate>`

                    :default value: 0.5
                    :type: float

                short_term_bias
                    see `short_term_bias <DualAdaptiveIntegrator.short_term_bias>`

                    :default value: 0.0
                    :type: float

                short_term_gain
                    see `short_term_gain <DualAdaptiveIntegrator.short_term_gain>`

                    :default value: 1.0
                    :type: float

                short_term_logistic
                    see `short_term_logistic <DualAdaptiveIntegrator.short_term_logistic>`

                    :default value: None
                    :type:

                short_term_rate
                    see `short_term_rate <DualAdaptiveIntegrator.short_term_rate>`

                    :default value: 0.9
                    :type: float

        """
        rate = Param(0.5, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        initial_short_term_avg = 0.0
        initial_long_term_avg = 0.0
        short_term_gain = Param(1.0, modulable=True)
        long_term_gain = Param(1.0, modulable=True)
        short_term_bias = Param(0.0, modulable=True)
        long_term_bias = Param(0.0, modulable=True)
        short_term_rate = Param(0.9, modulable=True)
        long_term_rate = Param(0.1, modulable=True)
        operation = PRODUCT
        offset = Param(0.0, modulable=True, aliases=[ADDITIVE_PARAM])
        previous_short_term_avg = None
        previous_long_term_avg = None
        short_term_logistic = None
        long_term_logistic = None


    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        RATE: None,
        # NOISE: None,
        OFFSET: None
    })

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 # rate: parameter_spec = 0.5,
                 # noise=0.0,
                 initializer=None,
                 initial_short_term_avg=0.0,
                 initial_long_term_avg=0.0,
                 short_term_gain=1.0,
                 long_term_gain=1.0,
                 short_term_bias=0.0,
                 long_term_bias=0.0,
                 short_term_rate=0.9,
                 long_term_rate=0.1,
                 operation=PRODUCT,
                 offset=0.0,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None):

        if not hasattr(self, "initializers"):
            self.initializers = ["initial_long_term_avg", "initial_short_term_avg"]

        if not hasattr(self, "stateful_attributes"):
            self.stateful_attributes = ["previous_short_term_avg", "previous_long_term_avg"]

        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(initializer=initializer,
                                                  # rate=rate,
                                                  # noise=noise,
                                                  offset=offset,
                                                  initial_short_term_avg=initial_short_term_avg,
                                                  initial_long_term_avg=initial_long_term_avg,
                                                  short_term_gain=short_term_gain,
                                                  long_term_gain=long_term_gain,
                                                  short_term_bias=short_term_bias,
                                                  long_term_bias=long_term_bias,
                                                  short_term_rate=short_term_rate,
                                                  long_term_rate=long_term_rate,
                                                  operation=operation,
                                                  params=params)

        self.previous_long_term_avg = self.initial_long_term_avg
        self.previous_short_term_avg = self.initial_short_term_avg

        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        self.has_initializers = True

    def _validate_params(self, request_set, target_set=None, context=None):

        # Handle list or array for rate specification
        if RATE in request_set:
            rate = request_set[RATE]
            if isinstance(rate, (list, np.ndarray)):
                if len(rate) != 1 and len(rate) != np.array(self.instance_defaults.variable).size:
                    # If the variable was not specified, then reformat it to match rate specification
                    #    and assign ClassDefaults.variable accordingly
                    # Note: this situation can arise when the rate is parametrized (e.g., as an array) in the
                    #       DualAdaptiveIntegrator's constructor, where that is used as a specification for a function parameter
                    #       (e.g., for an IntegratorMechanism), whereas the input is specified as part of the
                    #       object to which the function parameter belongs (e.g., the IntegratorMechanism);
                    #       in that case, the IntegratorFunction gets instantiated using its ClassDefaults.variable ([[0]]) before
                    #       the object itself, thus does not see the array specification for the input.
                    if self._default_variable_flexibility is DefaultsFlexibility.FLEXIBLE:
                        self._instantiate_defaults(variable=np.zeros_like(np.array(rate)), context=context)
                        if self.verbosePref:
                            warnings.warn(
                                "The length ({}) of the array specified for the rate parameter ({}) of {} "
                                "must match the length ({}) of the default input ({});  "
                                "the default input has been updated to match".format(
                                    len(rate),
                                    rate,
                                    self.name,
                                    np.array(self.instance_defaults.variable).size
                                ),
                                self.instance_defaults.variable
                            )
                    else:
                        raise FunctionError(
                            "The length ({}) of the array specified for the rate parameter ({}) of {} "
                            "must match the length ({}) of the default input ({})".format(
                                len(rate),
                                rate,
                                self.name,
                                np.array(self.instance_defaults.variable).size,
                                self.instance_defaults.variable,
                            )
                        )
                        # OLD:
                        # self.paramClassDefaults[RATE] = np.zeros_like(np.array(rate))

                        # KAM changed 5/15 b/c paramClassDefaults were being updated and *requiring* future integrator functions
                        # to have a rate parameter of type ndarray/list

        super()._validate_params(request_set=request_set,
                                 target_set=target_set,
                                 context=context)

        if RATE in target_set:
            # if isinstance(target_set[RATE], (list, np.ndarray)):
            #     for r in target_set[RATE]:
            #         if r < 0.0 or r > 1.0:
            #             raise FunctionError("The rate parameter ({}) (or all of its elements) of {} must be "
            #                                 "between 0.0 and 1.0 when integration_type is set to ADAPTIVE.".
            #                                 format(target_set[RATE], self.name))
            # else:
            #     if target_set[RATE] < 0.0 or target_set[RATE] > 1.0:
            #         raise FunctionError(
            #             "The rate parameter ({}) (or all of its elements) of {} must be between 0.0 and "
            #             "1.0 when integration_type is set to ADAPTIVE.".format(target_set[RATE], self.name))
            if not all_within_range(target_set[RATE], 0, 1):
                raise FunctionError("The rate parameter ({}) (or all of its elements) of {} "
                                    "must be in the interval [0,1]".format(target_set[RATE], self.name))

        if NOISE in target_set:
            noise = target_set[NOISE]
            if isinstance(noise, DistributionFunction):
                noise.owner = self
                target_set[NOISE] = noise._execute
            self._validate_noise(target_set[NOISE])
            # if INITIALIZER in target_set:
            #     self._validate_initializer(target_set[INITIALIZER])

        if OPERATION in target_set:
            if not target_set[OPERATION] in OPERATIONS:
                raise FunctionError("\'{}\' arg for {} must be one of the following: {}".
                                    format(OPERATION, self.name, OPERATIONS))

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """

        Arguments
        ---------

        variable : number, list or array : default ClassDefaults.variable
           a single value or array of values to be integrated.

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.

        Returns
        -------

        updated value of integral : 2d array

        """
        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)
        # rate = np.array(self.get_current_function_param(RATE, execution_id)).astype(float)
        # execute noise if it is a function
        # noise = self._try_execute_param(self.get_current_function_param(NOISE, execution_id), variable)
        short_term_rate = self.get_current_function_param("short_term_rate", execution_id)
        long_term_rate = self.get_current_function_param("long_term_rate", execution_id)

        # Integrate Short Term Utility:
        short_term_avg = self._EWMA_filter(short_term_rate,
                                           self.previous_short_term_avg,
                                           variable)
        # Integrate Long Term Utility:
        long_term_avg = self._EWMA_filter(long_term_rate,
                                          self.previous_long_term_avg,
                                          variable)

        value = self._combine_terms(short_term_avg, long_term_avg, execution_id=execution_id)

        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            self.parameters.previous_short_term_avg.set(short_term_avg, execution_id)
            self.parameters.previous_long_term_avg.set(long_term_avg, execution_id)

        return self.convert_output_type(value)

    def _combine_terms(self, short_term_avg, long_term_avg, execution_id=None):

        short_term_gain = self.get_current_function_param("short_term_gain", execution_id)
        short_term_bias = self.get_current_function_param("short_term_bias", execution_id)
        long_term_gain = self.get_current_function_param("long_term_gain", execution_id)
        long_term_bias = self.get_current_function_param("long_term_bias", execution_id)
        rate = self.get_current_function_param(RATE, execution_id)
        operation = self.get_current_function_param(OPERATION, execution_id)
        offset = self.get_current_function_param(OFFSET, execution_id)

        # s = 2*rate if rate <= 0.5 else 1
        # l = 2-(2*rate) if rate >= 0.5 else 1

        short_term_logistic = self._logistic(variable=short_term_avg,
                                             gain=short_term_gain,
                                             bias=short_term_bias,
                                             )
        self.parameters.short_term_logistic.set(short_term_logistic, execution_id)

        long_term_logistic = self._logistic(variable=long_term_avg,
                                            gain=long_term_gain,
                                            bias=long_term_bias,
                                            )
        self.parameters.long_term_logistic.set(long_term_logistic, execution_id)

        if operation == PRODUCT:
            value = (1 - short_term_logistic) * long_term_logistic
        elif operation == SUM:
            value = (1 - short_term_logistic) + long_term_logistic
        elif operation == S_MINUS_L:
            value = (1 - short_term_logistic) - long_term_logistic
        elif operation == L_MINUS_S:
            value = long_term_logistic - (1 - short_term_logistic)

        return value + offset

    def reinitialize(self, short=None, long=None, execution_context=None):

        """
        Effectively begins accumulation over again at the specified utilities.

        Sets `previous_short_term_avg <DualAdaptiveIntegrator.previous_short_term_avg>` to the quantity specified
        in the first argument and `previous_long_term_avg <DualAdaptiveIntegrator.previous_long_term_avg>` to the
        quantity specified in the second argument.

        Sets `value <DualAdaptiveIntegrator.value>` by computing it based on the newly updated values for
        `previous_short_term_avg <DualAdaptiveIntegrator.previous_short_term_avg>` and
        `previous_long_term_avg <DualAdaptiveIntegrator.previous_long_term_avg>`.

        If no arguments are specified, then the current values of `initial_short_term_avg
        <DualAdaptiveIntegrator.initial_short_term_avg>` and `initial_long_term_avg
        <DualAdaptiveIntegrator.initial_long_term_avg>` are used.
        """

        if short is None:
            short = self.get_current_function_param("initial_short_term_avg", execution_context)
        if long is None:
            long = self.get_current_function_param("initial_long_term_avg", execution_context)

        self.parameters.previous_short_term_avg.set(short, execution_context)
        self.parameters.previous_long_term_avg.set(long, execution_context)
        value = self._combine_terms(short, long)

        self.parameters.value.set(value, execution_context, override=True)
        return value


class InteractiveActivationIntegrator(IntegratorFunction):  # ----------------------------------------------------------
    """
    InteractiveActivationIntegrator(      \
        default_variable=None,  \
        rate=1.0,               \
        decay=1.0,              \
        rest=0.0,               \
        max_val=1.0,            \
        min_val=-1.0,           \
        noise=0.0,              \
        initializer,            \
        params=None,            \
        owner=None,             \
        prefs=None,             \
        )

    .. _InteractiveActivationIntegrator:

    Implements a generalized version of the interactive activation from `McClelland and Rumelhart (1981)
    <http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.298.4480&rep=rep1&type=pdf>`_ that integrates current
    value of `variable <InteractiveActivationIntegrator.variable>` toward an asymptotic maximum value `max_val
    <InteractiveActivationIntegrator.max_val>` for positive inputs and toward an asymptotic mininum value (`min_val
    <InteractiveActivationIntegrator.min_val>`) for negative inputs, and decays asymptotically towards an intermediate
    resting value (`rest <InteractiveActivationIntegrator.rest>`).

    `function <InteractiveActivationIntegrator.function>` returns:

    .. math::
        previous\_value + (rate * (variable + noise) * distance\_from\_asymptote) - (decay * distance\_from\_rest)

    where:

    .. math::
        if\ variable > 0,\ distance\_from\_asymptote = max\_val - previous\_value

    .. math::
        if\ variable < 0,\ distance\_from\_asymptote = previous\_value - min\_val

    .. math::
        if\ variable = 0,\ distance\_from\_asymptote = 0


    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for the value to be integrated;  if it is a list or array, each element is independently
        integrated.

    rate : float, list or 1d array : default 1.0
        specifies the rate of change in activity; its value(s) must be in the interval [0,1].  If it is a list or
        array, it must be the same length as `variable <InteractiveActivationIntegrator.variable>`.

    decay : float, list or 1d array : default 1.0
        specifies the rate of at which activity decays toward `rest <InteractiveActivationIntegrator.rest>`.
        If it is a list or array, it must be the same length as `variable <InteractiveActivationIntegrator.variable>`;
        its value(s) must be in the interval [0,1].

    rest : float, list or 1d array : default 0.0
        specifies the initial value and one toward which value `decays <InteractiveActivationIntegrator.decay>`.
        If it is a list or array, it must be the same length as `variable <InteractiveActivationIntegrator.variable>`.
        COMMENT:
        its value(s) must be between `max_val <InteractiveActivationIntegrator.max_val>` and `min_val
        <InteractiveActivationIntegrator.min_val>`.
        COMMENT

    max_val : float, list or 1d array : default 1.0
        specifies the maximum asymptotic value toward which integration occurs for positive values of `variable
        <InteractiveActivationIntegrator.variable>`.  If it is a list or array, it must be the same length as `variable
        <InteractiveActivationIntegrator.variable>`; all values must be greater than the corresponding values of
        `min_val <InteractiveActivationIntegrator.min_val>` (see `max_val <InteractiveActivationIntegrator.max_val>`
        for details).

    min_val : float, list or 1d array : default 1.0
        specifies the minimum asymptotic value toward which integration occurs for negative values of `variable
        <InteractiveActivationIntegrator.variable>`.  If it is a list or array, it must be the same length as `variable
        <InteractiveActivationIntegrator.variable>`; all values must be greater than the corresponding values of
        `max_val <InteractiveActivationIntegrator.min_val>` (see `max_val <InteractiveActivationIntegrator.min_val>`
        for details).

    noise : float, function, list or 1d array : default 0.0
        specifies random value added to `variable <InteractiveActivationIntegrator.noise>` in each call to `function
        <InteractiveActivationIntegrator.function>`; if it is a list or array, it must be the same length as `variable
        <IntegratorFunction.variable>` (see `noise <Integrator_Noise>` for details).

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration.  If it is a list or array, it must be the same length as
        `default_variable <InteractiveActivationIntegrator.variable>` (see `initializer <Integrator_Initializer>`
        for details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        current input value some portion of which (determined by `rate <InteractiveActivationIntegrator.rate>`) will be
        added to the prior value;  if it is an array, each element is independently integrated.

    rate : float or 1d array in interval [0,1]
        determines the rate at which activity increments toward either `max_val
        <InteractiveActivationIntegrator.max_val>` (`variable <InteractiveActivationIntegrator.variable>` is
        positive) or `min_val <InteractiveActivationIntegrator.min_val>` (if `variable
        <InteractiveActivationIntegrator.variable>` is negative).  If it is a float or has a single element, it is
        applied to all elements of `variable <InteractiveActivationIntegrator.variable>`; if it has more than one
        element, each element is applied to the corresponding element of `variable
        <InteractiveActivationIntegrator.variable>`. Serves as *MULTIPLICATIVE_PARAM* for `modulation
        <ModulatorySignal_Modulation>` of `function <InteractiveActivationIntegrator.function>`.

    decay : float or 1d array
        determines the rate of at which activity decays toward `rest <InteractiveActivationIntegrator.rest>` (similary
        to *rate* in other IntegratorFuncgtions).  If it is a float or has a single element, it applies to all elements
        of `variable <InteractiveActivationIntegrator.variable>`;  if it has more than one element, each element applies
        to the corresponding element of `variable <InteractiveActivationIntegrator.variable>`.

    rest : float or 1d array
        determines the initial value and one toward which value `decays <InteractiveActivationIntegrator.decay>`
        (similar to *bias* in other IntegratorFunctions).  If it is a float or has a single element, it applies to
        all elements of `variable <InteractiveActivationIntegrator.variable>`;  if it has more than one element,
        each element applies to the corresponding element of `variable <InteractiveActivationIntegrator.variable>`.

    max_val : float or 1d array
        determines the maximum asymptotic value toward which integration occurs for positive values of `variable
        <InteractiveActivationIntegrator.variable>`.  If it is a float or has a single element, it applies to all
        elements of `variable <InteractiveActivationIntegrator.variable>`;  if it has more than one element,
        each element applies to the corresponding element of `variable <InteractiveActivationIntegrator.variable>`.

    min_val : float or 1d array
        determines the minimum asymptotic value toward which integration occurs for negative values of `variable
        <InteractiveActivationIntegrator.variable>`.  If it is a float or has a single element, it applies to all
        elements of `variable <InteractiveActivationIntegrator.variable>`;  if it has more than one element,
        each element applies to the corresponding element of `variable <InteractiveActivationIntegrator.variable>`.

    noise : float, Function or 1d array
        random value added to `variable <InteractiveActivationIntegrator.noise>` in each call to `function
        <InteractiveActivationIntegrator.function>` (see `noise <Integrator_Noise>` for details).

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value(s) to which `previous_value
        <InteractiveActivationIntegrator.previous_value>` is set (see `initializer <Integrator_Initializer>`
        for details).

    previous_value : 1d array : default ClassDefaults.variable
        stores previous value with which `variable <InteractiveActivationIntegrator.variable>` is integrated.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = INTERACTIVE_ACTIVATION_INTEGRATOR_FUNCTION

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        RATE: None,
        DECAY: None,
        REST: None,
        NOISE: None,
    })

    multiplicative_param = RATE
    # additive_param = OFFSET

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                decay
                    see `decay <InteractiveActivationIntegrator.decay>`

                    :default value: 1.0
                    :type: float

                max_val
                    see `max_val <InteractiveActivationIntegrator.max_val>`

                    :default value: 1.0
                    :type: float

                min_val
                    see `min_val <InteractiveActivationIntegrator.min_val>`

                    :default value: 1.0
                    :type: float

                rate
                    see `rate <InteractiveActivationIntegrator.rate>`

                    :default value: 1.0
                    :type: float

                rest
                    see `rest <InteractiveActivationIntegrator.rest>`

                    :default value: 0.0
                    :type: float

        """
        rate = Param(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        decay = Param(1.0, modulable=True)
        rest = Param(0.0, modulable=True, aliases=[ADDITIVE_PARAM])
        max_val = Param(1.0)
        min_val = Param(1.0)

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 rate: parameter_spec = 1.0,
                 decay: parameter_spec = 0.0,
                 rest: parameter_spec = 0.0,
                 max_val: parameter_spec = 1.0,
                 min_val: parameter_spec = -1.0,
                 noise=0.0,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None,
                 # **kwargs
                 ):

        # # This may be passed (as standard IntegratorFunction arg) but is not used by IA
        # unsupported_args = {OFFSET}
        # if any(k in unsupported_args for k in kwargs):
        #     s = 's' if len(kwargs)>1 else ''
        #     warnings.warn("{} arg{} not supported in {}".
        #                   format(repr(", ".join(list(kwargs.keys()))),s, self.__class__.__name__))
        #     for k in unsupported_args:
        #         if k in kwargs:
        #             del kwargs[k]


        if initializer is None:
            initializer = rest
        if default_variable is None:
            default_variable = initializer

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(rate=rate,
                                                  decay=decay,
                                                  rest=rest,
                                                  max_val=max_val,
                                                  min_val=min_val,
                                                  initializer=initializer,
                                                  noise=noise,
                                                  # offset=offset,
                                                  params=params)

        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        self.has_initializers = True

    def _validate_params(self, request_set, target_set=None, context=None):

        super()._validate_params(request_set=request_set, target_set=target_set,context=context)

        if RATE in request_set and request_set[RATE] is not None:
            rate = request_set[RATE]
            if np.isscalar(rate):
                rate = [rate]
            if not all_within_range(rate, 0, 1):
                raise FunctionError("Value(s) specified for {} argument of {} ({}) must be in interval [0,1]".
                                    format(repr(RATE), self.__class__.__name__, rate))

        if DECAY in request_set and request_set[DECAY] is not None:
            decay = request_set[DECAY]
            if np.isscalar(decay):
                decay = [decay]
            if not all(0.0 <= d <= 1.0 for d in decay):
                raise FunctionError("Value(s) specified for {} argument of {} ({}) must be in interval [0,1]".
                                    format(repr(DECAY), self.__class__.__name__, decay))

    def function(self, variable=None, execution_id=None, params=None, context=None):
        """

        Arguments
        ---------

        variable : number, list or array : default ClassDefaults.variable
           a single value or array of values to be integrated.

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.

        Returns
        -------

        updated value of integral : 2d array

        """

        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)

        rate = np.array(self.get_current_function_param(RATE, execution_id)).astype(float)
        decay = np.array(self.get_current_function_param(DECAY, execution_id)).astype(float)
        rest = np.array(self.get_current_function_param(REST, execution_id)).astype(float)
        # FIX: only works with "max_val". Keyword MAX_VAL = "MAX_VAL", not max_val
        max_val = np.array(self.get_current_function_param("max_val", execution_id)).astype(float)
        min_val = np.array(self.get_current_function_param("min_val", execution_id)).astype(float)

        # execute noise if it is a function
        noise = self._try_execute_param(self.get_current_function_param(NOISE, execution_id), variable)

        current_input = variable

        # FIX: ?CLEAN THIS UP BY SETTING initializer IN __init__ OR OTHER RELEVANT PLACE?
        if self.context.initialization_status == ContextFlags.INITIALIZING:
            if rest.ndim == 0 or len(rest)==1:
                # self.parameters.previous_value.set(np.full_like(current_input, rest), execution_id)
                self._initialize_previous_value(np.full_like(current_input, rest), execution_id)
            elif np.atleast_2d(rest).shape == current_input.shape:
                # self.parameters.previous_value.set(rest, execution_id)
                self._initialize_previous_value(rest, execution_id)
            else:
                raise FunctionError("The {} argument of {} ({}) must be an int or float, "
                                    "or a list or array of the same length as its variable ({})".
                                    format(repr(REST), self.__class__.__name__, rest, len(variable)))
        previous_value = self.get_previous_value(execution_id)

        current_input = np.atleast_2d(variable)
        prev_val = np.atleast_2d(previous_value)

        dist_from_asymptote = np.zeros_like(current_input, dtype=float)
        for i in range(len(current_input)):
            for j in range(len(current_input[i])):
                if current_input[i][j] > 0:
                    d = max_val - prev_val[i][j]
                elif current_input[i][j] < 0:
                    d = prev_val[i][j] - min_val
                else:
                    d = 0
                dist_from_asymptote[i][j] = d

        dist_from_rest = prev_val - rest

        new_value = previous_value + (rate * (current_input + noise) * dist_from_asymptote) - (decay * dist_from_rest)

        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            self.parameters.previous_value.set(new_value, execution_id)

        return self.convert_output_type(new_value)


class DriftDiffusionIntegrator(IntegratorFunction):  # -----------------------------------------------------------------
    """
    DriftDiffusionIntegrator(           \
        default_variable=None,          \
        rate=1.0,                       \
        noise=0.0,                      \
        offset= 0.0,                    \
        starting_point=0.0,             \
        threshold=1.0                   \
        time_step_size=1.0,             \
        initializer,                    \
        params=None,                    \
        owner=None,                     \
        prefs=None,                     \
        )

    .. _DriftDiffusionIntegrator:

    Accumulate "evidence" to a bound.  `function <DriftDiffusionIntegrator.function>` returns one
    time step of integration:

    ..  math::
        previous\\_value + rate \\cdot variable \\cdot time\\_step\\_size + \\mathcal{N}(\\sigma^2)

    where

    ..  math::
        \\sigma^2 =\\sqrt{time\\_step\\_size \\cdot noise}

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `rate <AdaptiveIntegrator.rate>`
    | *ADDITIVE_PARAM:* `offset <AdaptiveIntegrator.offset>`
    |

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies the stimulus component of drift rate -- the drift rate is the product of variable and rate

    rate : float, list or 1d array : default 1.0
        applied multiplicatively to `variable <DriftDiffusionIntegrator.variable>`;  If it is a list or array, it must
        be the same length as `variable <DriftDiffusionIntegrator.variable>` (see `rate <DriftDiffusionIntegrator.rate>`
        for details).

    noise : float : default 0.0
        specifies a value by which to scale the normally distributed random value added to the integral in each call to
        `function <DriftDiffusionIntegrator.function>` (see `noise <DriftDiffusionIntegrator.noise>` for details).

    COMMENT:
    FIX: REPLACE ABOVE WITH THIS ONCE LIST/ARRAY SPECIFICATION OF NOISE IS FULLY IMPLEMENTED
    noise : float, list or 1d array : default 0.0
        specifies a value by which to scale the normally distributed random value added to the integral in each call to
        `function <DriftDiffusionIntegrator.function>`; if it is a list or array, it must be the same length as
        `variable <DriftDiffusionIntegrator.variable>` (see `noise <DriftDiffusionIntegrator.noise>` for details).
    COMMENT

    offset : float, list or 1d array : default 0.0
        specifies constant value added to integral in each call to `function <DriftDiffusionIntegrator.function>`
        if it's absolute value is below `threshold <DriftDiffusionIntegrator.threshold>`;
        if it is a list or array, it must be the same length as `variable <DriftDiffusionIntegrator.variable>`
        (see `offset <DriftDiffusionIntegrator.offset>` for details).

    starting_point : float, list or 1d array:  default 0.0
        determspecifies ines the starting value for the integration process; if it is a list or array, it must be the
        same length as `variable <DriftDiffusionIntegrator.variable>` (see `starting_point
        <DriftDiffusionIntegrator.starting_point>` for details).

    threshold : float : default 0.0
        specifies the threshold (boundaries) of the drift diffusion process -- i.e., at which the
        integration process terminates (see `threshold <DriftDiffusionIntegrator.threshold>` for details).

    time_step_size : float : default 0.0
        specifies the timing precision of the integration process (see `time_step_size
        <DriftDiffusionIntegrator.time_step_size>` for details.

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration.  If it is a list or array, it must be the same length as
        `default_variable <DriftDiffusionIntegrator.variable>` (see `initializer <Integrator_Initializer>`
        for details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : float or array
        current input value (can be thought of as implementing the stimulus component of the drift rate);  if it is an
        array, each element represents an independently integrated decision variable.

    rate : float or 1d array
        applied multiplicatively to `variable <DriftDiffusionIntegrator.variable>` (can be thought of as implementing
        the attentional component of the drift rate).  If it is a float or has a single element, its value is applied
        to all the elements of `variable <DriftDiffusionIntegrator.variable>`; if it is an array, each element is
        applied to the corresponding element of `variable <DriftDiffusionIntegrator.variable>`. Serves as
        *MULTIPLICATIVE_PARAM* for `modulation <ModulatorySignal_Modulation>` of `function
        <DriftDiffusionIntegrator.function>`.

    noise : float
        scales the normally distributed random value added to integral in each call to `function
        <DriftDiffusionIntegrator.function>`.  A single random term is generated each execution, and applied to all
        elements of `variable <DriftDiffusionIntegrator.variable>` if that is an array with more than one element.

    COMMENT:
    FIX: REPLACE ABOVE WITH THIS ONCE LIST/ARRAY SPECIFICATION OF NOISE IS FULLY IMPLEMENTED
    noise : float or 1d array
        scales the normally distributed random value added to integral in each call to `function
        <DriftDiffusionIntegrator.function>`. If `variable <DriftDiffusionIntegrator.variable>` is a list or array,
        and noise is a float, a single random term is generated and applied for each element of `variable
        <DriftDiffusionIntegrator.variable>`.  If noise is a list or array, it must be the same length as `variable
        <DriftDiffusionIntegrator.variable>`, and a separate random term scaled by noise is applied for each of the
        corresponding elements of `variable <DriftDiffusionIntegrator.variable>`.
    COMMENT

    offset : float or 1d array
        constant value added to integral in each call to `function <DriftDiffusionIntegrator.function>`
        if it's absolute value is below `threshold <DriftDiffusionIntegrator.threshold>`.
        If `variable <DriftDiffusionIntegrator.variable>` is an array and offset is a float, offset is applied
        to each element of the integral;  if offset is a list or array, each of its elements is applied to each of
        the corresponding elements of the integral (i.e., Hadamard addition). Serves as *ADDITIVE_PARAM* for
        `modulation <ModulatorySignal_Modulation>` of `function <DriftDiffusionIntegrator.function>`.

    starting_point : float or 1d array
        determines the start the starting value for the integration process; if it is a list or array, it must be the
        same length as `variable <DriftDiffusionIntegrator.variable>`. If `variable <DriftDiffusionIntegrator.variable>`
        is an array and starting_point is a float, starting_point is used for each element of the integral;  if
        starting_point is a list or array, each of its elements is used as the starting point for each element of the
        integral.

    threshold : float
        determines the boundaries of the drift diffusion process:  the integration process can be scheduled to
        terminate when the result of `function <DriftDiffusionIntegrator.function>` equals or exceeds either the
        positive or negative value of threshold (see hint).

        .. hint::
           For a Mechanism to terminate execution when the DriftDiffusionIntegrator reaches its threshold, the
           `function <DriftDiffusionIntegrator.function>`, the `Mechanism` to which it assigned must belong to a
           `System` or `Composition` with a `Scheduler <Scheduler>` that applies the `WhenFinished <WhenFinished>`
           `Condition <Condition>` to that Mechanism.

    time_step_size : float
        determines the timing precision of the integration process and is used to scale the `noise
        <DriftDiffusionIntegrator.noise>` parameter according to the standard DDM probability distribution.

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value(s) to which `previous_value
        <DriftDiffusionIntegrator.previous_value>` is set (see `initializer <Integrator_Initializer>` for details).

    previous_time : float
        stores previous time at which the function was executed and accumulates with each execution according to
        `time_step_size <DriftDiffusionIntegrator.default_time_step_size>`.

    previous_value : 1d array : default ClassDefaults.variable
        stores previous value with which `variable <DriftDiffusionIntegrator.variable>` is integrated.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = DRIFT_DIFFUSION_INTEGRATOR_FUNCTION

    multiplicative_param = RATE
    additive_param = OFFSET

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                offset
                    see `offset <DriftDiffusionIntegrator.offset>`

                    :default value: 0.0
                    :type: float

                previous_time
                    see `previous_time <DriftDiffusionIntegrator.previous_time>`

                    :default value: None
                    :type:

                rate
                    see `rate <DriftDiffusionIntegrator.rate>`

                    :default value: 1.0
                    :type: float

                starting_point
                    see `starting_point <DriftDiffusionIntegrator.starting_point>`

                    :default value: 0.0
                    :type: float

                threshold
                    see `threshold <DriftDiffusionIntegrator.threshold>`

                    :default value: 100.0
                    :type: float

                time_step_size
                    see `time_step_size <DriftDiffusionIntegrator.time_step_size>`

                    :default value: 1.0
                    :type: float

        """
        rate = Param(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        offset = Param(0.0, modulable=True, aliases=[ADDITIVE_PARAM])
        starting_point = 0.0
        threshold = Param(100.0, modulable=True)
        time_step_size = Param(1.0, modulable=True)
        previous_time = None

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        NOISE: None,
        RATE: None
    })

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 rate: parameter_spec = 1.0,
                 noise=0.0,
                 offset: parameter_spec = 0.0,
                 starting_point=0.0,
                 threshold=100.0,
                 time_step_size=1.0,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None):

        if not hasattr(self, "initializers"):
            self.initializers = ["initializer", "starting_point"]

        if not hasattr(self, "stateful_attributes"):
            self.stateful_attributes = ["previous_value", "previous_time"]

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(rate=rate,
                                                  time_step_size=time_step_size,
                                                  starting_point=starting_point,
                                                  initializer=initializer,
                                                  threshold=threshold,
                                                  noise=noise,
                                                  offset=offset,
                                                  params=params)

        # Assign here as default, for use in initialization of function
        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        self.has_initializers = True

    @property
    def output_type(self):
        return self._output_type

    @output_type.setter
    def output_type(self, value):
        # disabled because it happens during normal execution, may be confusing
        # warnings.warn('output_type conversion disabled for {0}'.format(self.__class__.__name__))
        self._output_type = None

    def _validate_noise(self, noise):
        if not isinstance(noise, float):
            raise FunctionError(
                "Invalid noise parameter for {}. DriftDiffusionIntegrator requires noise parameter to be a float. Noise"
                " parameter is used to construct the standard DDM noise distribution".format(self.name))

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """

        Arguments
        ---------

        variable : number, list or array : default ClassDefaults.variable
           a single value or array of values to be integrated (can be thought of as the stimulus component of
           the drift rate).

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.

        Returns
        -------

        updated value of integral : 2d array

        """
        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)

        rate = np.array(self.get_current_function_param(RATE, execution_id)).astype(float)
        noise = self.get_current_function_param(NOISE, execution_id)
        offset = self.get_current_function_param(OFFSET, execution_id)
        threshold = self.get_current_function_param(THRESHOLD, execution_id)
        time_step_size = self.get_current_function_param(TIME_STEP_SIZE, execution_id)

        previous_value = np.atleast_2d(self.get_previous_value(execution_id))

        value = previous_value + rate * variable * time_step_size \
                + np.sqrt(time_step_size * noise) * np.random.normal()

        if np.all(abs(value) < threshold):
            adjusted_value = value + offset
        elif np.all(value >= threshold):
            adjusted_value = np.atleast_2d(threshold)
        elif np.all(value <= -threshold):
            adjusted_value = np.atleast_2d(-threshold)

        # If this NOT an initialization run, update the old value and time
        # If it IS an initialization run, leave as is
        #    (don't want to count it as an execution step)
        previous_time = self.get_current_function_param('previous_time', execution_id)
        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            previous_value = adjusted_value
            previous_time = previous_time + time_step_size
            if not np.isscalar(variable):
                previous_time = np.broadcast_to(
                    previous_time,
                    variable.shape
                ).copy()

            self.parameters.previous_time.set(previous_time, execution_id)

        self.parameters.previous_value.set(previous_value, execution_id)
        return previous_value, previous_time


class OrnsteinUhlenbeckIntegrator(IntegratorFunction):  # --------------------------------------------------------------
    """
    OrnsteinUhlenbeckIntegrator(         \
        default_variable=None,           \
        rate=1.0,                        \
        decay=1.0,                       \
        noise=0.0,                       \
        offset= 0.0,                     \
        starting_point=0.0,              \
        time_step_size=1.0,              \
        initializer=0.0,                 \
        params=None,                     \
        owner=None,                      \
        prefs=None,                      \
        )

    .. _OrnsteinUhlenbeckIntegrator:

    `function <_OrnsteinUhlenbeckIntegrator.function>` returns one time step of integration according to an
    `Ornstein Uhlenbeck process <https://en.wikipedia.org/wiki/Ornstein%E2%80%93Uhlenbeck_process>`_:

    .. math::
       previous\\_value + (decay \\cdot  previous\\_value) - (rate \\cdot variable) + \\mathcal{N}(\\sigma^2)
    where
    ..  math::
        \\sigma^2 =\\sqrt{time\\_step\\_size \\cdot noise}

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `rate <AdaptiveIntegrator.rate>`
    | *ADDITIVE_PARAM:* `offset <AdaptiveIntegrator.offset>`
    |

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for  the stimulus component of drift rate -- the drift rate is the product of variable and
        rate

    rate : float, list or 1d array : default 1.0
        specifies value applied multiplicatively to `variable <OrnsteinUhlenbeckIntegrator.variable>`;  If it is a
        list or array, it must be the same length as `variable <OrnsteinUhlenbeckIntegrator.variable>` (see `rate
        <OrnsteinUhlenbeckIntegrator.rate>` for details).

    decay : float, list or 1d array : default 1.0
        specifies value applied multiplicatively to `previous_value <OrnsteinUhlenbeckIntegrator.previous_value>`;
        If it is a list or array, it must be the same length as `variable <OrnsteinUhlenbeckIntegrator.variable>` (
        see `decay <OrnsteinUhlenbeckIntegrator.rate>` for details).

    noise : float : default 0.0
        specifies a value by which to scale the normally distributed random value added to the integral in each call to
        `function <OrnsteinUhlenbeckIntegrator.function>` (see `noise <OrnsteinUhlenbeckIntegrator.noise>` for details).

    COMMENT:
    FIX: REPLACE ABOVE WITH THIS ONCE LIST/ARRAY SPECIFICATION OF NOISE IS FULLY IMPLEMENTED
    noise : float, list or 1d array : default 0.0
        specifies a value by which to scale the normally distributed random value added to the integral in each call to
        `function <OrnsteinUhlenbeckIntegrator.function>`; if it is a list or array, it must be the same length as
        `variable <OrnsteinUhlenbeckIntegrator.variable>` (see `noise <OrnsteinUhlenbeckIntegrator.noise>` for details).
    COMMENT

    offset : float, list or 1d array : default 0.0
        specifies a constant value added to integral in each call to `function <OrnsteinUhlenbeckIntegrator.function>`;
        if it is a list or array, it must be the same length as `variable <OrnsteinUhlenbeckIntegrator.variable>`
        (see `offset <OrnsteinUhlenbeckIntegrator.offset>` for details)

    starting_point : float : default 0.0
        specifies the starting time of the model and is used to compute `previous_time
        <OrnsteinUhlenbeckIntegrator.previous_time>`

    time_step_size : float : default 0.0
        determines the timing precision of the integration process (see `time_step_size
        <OrnsteinUhlenbeckIntegrator.time_step_size>` for details.

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration.  If it is a list or array, it must be the same length as
        `default_variable <OrnsteinUhlenbeckIntegrator.variable>` (see `initializer <Integrator_Initializer>`
        for details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        represents the stimulus component of drift. The product of
        `variable <OrnsteinUhlenbeckIntegrator.variable>` and `rate <OrnsteinUhlenbeckIntegrator.rate>` is multiplied
        by `time_step_size <OrnsteinUhlenbeckIntegrator.time_step_size>` to model the accumulation of evidence during
        one step.

    rate : float or 1d array
        applied multiplicatively to `variable <OrnsteinUhlenbeckIntegrator.variable>`.  If it is a float or has a
        single element, its value is applied to all the elements of `variable <OrnsteinUhlenbeckIntegrator.variable>`;
        if it is an array, each element is applied to the corresponding element of `variable
        <OrnsteinUhlenbeckIntegrator.variable>`.  Serves as *MULTIPLICATIVE_PARAM* for `modulation
        <ModulatorySignal_Modulation>` of `function <OrnsteinUhlenbeckIntegrator.function>`.

    decay : float or 1d array
        applied multiplicatively to `previous_value <OrnsteinUhlenbeckIntegrator.previous_value>`; If it is a float or
        has a single element, its value is applied to all the elements of `previous_value
        <OrnsteinUhlenbeckIntegrator.previous_value>`; if it is an array, each element is applied to the corresponding
        element of `previous_value <OrnsteinUhlenbeckIntegrator.previous_value>`.

    noise : float
        scales the normally distributed random value added to integral in each call to `function
        <OrnsteinUhlenbeckIntegrator.function>`.  A single random term is generated each execution, and applied to all
        elements of `variable <OrnsteinUhlenbeckIntegrator.variable>` if that is an array with more than one element.

    COMMENT:
    FIX: REPLACE ABOVE WITH THIS ONCE LIST/ARRAY SPECIFICATION OF NOISE IS FULLY IMPLEMENTED
    noise : float or 1d array
        scales the normally distributed random value added to integral in each call to `function
        <OrnsteinUhlenbeckIntegrator.function>`. If `variable <OrnsteinUhlenbeckIntegrator.variable>` is a list or
        array, and noise is a float, a single random term is generated and applied for each element of `variable
        <OrnsteinUhlenbeckIntegrator.variable>`.  If noise is a list or array, it must be the same length as `variable
        <OrnsteinUhlenbeckIntegrator.variable>`, and a separate random term scaled by noise is applied for each of the
        corresponding elements of `variable <OrnsteinUhlenbeckIntegrator.variable>`.
    COMMENT

    offset : float or 1d array
        constant value added to integral in each call to `function <OrnsteinUhlenbeckIntegrator.function>`.
        If `variable <OrnsteinUhlenbeckIntegrator.variable>` is an array and offset is a float, offset is applied
        to each element of the integral;  if offset is a list or array, each of its elements is applied to each of
        the corresponding elements of the integral (i.e., Hadamard addition). Serves as *ADDITIVE_PARAM* for
        `modulation <ModulatorySignal_Modulation>` of `function <OrnsteinUhlenbeckIntegrator.function>`.

    starting_point : float
        determines the start time of the integration process.

    time_step_size : float
        determines the timing precision of the integration process and is used to scale the `noise
        <OrnsteinUhlenbeckIntegrator.noise>` parameter appropriately.

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value(s) to which `previous_value
        <OrnsteinUhlenbeckIntegrator.previous_value>` is set (see `initializer <Integrator_Initializer>` for details).

    previous_value : 1d array : default ClassDefaults.variable
        stores previous value with which `variable <OrnsteinUhlenbeckIntegrator.variable>` is integrated.

    previous_time : float
        stores previous time at which the function was executed and accumulates with each execution according to
        `time_step_size <OrnsteinUhlenbeckIntegrator.default_time_step_size>`.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = ORNSTEIN_UHLENBECK_INTEGRATOR_FUNCTION

    multiplicative_param = RATE
    additive_param = OFFSET

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                decay
                    see `decay <OrnsteinUhlenbeckIntegrator.decay>`

                    :default value: 1.0
                    :type: float

                offset
                    see `offset <OrnsteinUhlenbeckIntegrator.offset>`

                    :default value: 0.0
                    :type: float

                previous_time
                    see `previous_time <OrnsteinUhlenbeckIntegrator.previous_time>`

                    :default value: 0.0
                    :type: float

                rate
                    see `rate <OrnsteinUhlenbeckIntegrator.rate>`

                    :default value: 1.0
                    :type: float

                starting_point
                    see `starting_point <OrnsteinUhlenbeckIntegrator.starting_point>`

                    :default value: 0.0
                    :type: float

                time_step_size
                    see `time_step_size <OrnsteinUhlenbeckIntegrator.time_step_size>`

                    :default value: 1.0
                    :type: float

        """
        rate = Param(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        decay = Param(1.0, modulable=True)
        offset = Param(0.0, modulable=True, aliases=[ADDITIVE_PARAM])
        time_step_size = Param(1.0, modulable=True)
        starting_point = 0.0
        previous_time = 0.0

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        NOISE: None,
        RATE: None
    })

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 rate: parameter_spec = 1.0,
                 decay=1.0,
                 noise=0.0,
                 offset: parameter_spec = 0.0,
                 starting_point=0.0,
                 time_step_size=1.0,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None):

        if not hasattr(self, "initializers"):
            self.initializers = ["initializer", "starting_point"]

        if not hasattr(self, "stateful_attributes"):
            self.stateful_attributes = ["previous_value", "previous_time"]

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(rate=rate,
                                                  decay=decay,
                                                  noise=noise,
                                                  offset=offset,
                                                  starting_point=starting_point,
                                                  time_step_size=time_step_size,
                                                  initializer=initializer,
                                                  params=params)

        # Assign here as default, for use in initialization of function
        self.previous_value = initializer
        self.previous_time = starting_point

        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        self.previous_time = self.starting_point
        self.has_initializers = True

    def _validate_noise(self, noise):
        if not isinstance(noise, float):
            raise FunctionError(
                "Invalid noise parameter for {}. OrnsteinUhlenbeckIntegrator requires noise parameter to be a float. "
                "Noise parameter is used to construct the standard DDM noise distribution".format(self.name))

    @property
    def output_type(self):
        return self._output_type

    @output_type.setter
    def output_type(self, value):
        # disabled because it happens during normal execution, may be confusing
        # warnings.warn('output_type conversion disabled for {0}'.format(self.__class__.__name__))
        self._output_type = None

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """

        Arguments
        ---------

        variable : number, list or array : default ClassDefaults.variable
           a single value or array of values to be integrated.

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.


        Returns
        -------

        updated value of integral : 2d array

        """

        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)
        rate = np.array(self.get_current_function_param(RATE, execution_id)).astype(float)
        decay = self.get_current_function_param(DECAY, execution_id)
        noise = self.get_current_function_param(NOISE, execution_id)
        offset = self.get_current_function_param(OFFSET, execution_id)
        time_step_size = self.get_current_function_param(TIME_STEP_SIZE, execution_id)

        previous_value = np.atleast_2d(self.get_previous_value(execution_id))

        # dx = (lambda*x + A)dt + c*dW
        value = previous_value + (decay * previous_value - rate * variable) * time_step_size + np.sqrt(
            time_step_size * noise) * np.random.normal()

        # If this NOT an initialization run, update the old value and time
        # If it IS an initialization run, leave as is
        #    (don't want to count it as an execution step)
        adjusted_value = value + offset

        previous_time = self.get_current_function_param('previous_time', execution_id)
        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            previous_value = adjusted_value
            previous_time = previous_time + time_step_size
            if not np.isscalar(variable):
                previous_time = np.broadcast_to(
                    previous_time,
                    variable.shape
                ).copy()
            self.parameters.previous_time.set(previous_time, execution_id)

        self.parameters.previous_value.set(previous_value, execution_id)
        return previous_value, previous_time


class LeakyCompetingIntegrator(IntegratorFunction):  # -----------------------------------------------------------------
    """
    LeakyCompetingIntegrator(                  \
        default_variable=None,      \
        rate=1.0,                   \
        noise=0.0,                  \
        offset=None,                \
        time_step_size=0.1,         \
        initializer=0.0,            \
        params=None,                \
        owner=None,                 \
        prefs=None,                 \
        )

    .. _LeakyCompetingIntegrator:

    Implements Leaky Competitive Accumulator (LCA) described in `Usher & McClelland (2001)
    <https://www.ncbi.nlm.nih.gov/pubmed/11488378>`_.  `function <LeakyCompetingIntegrator.function>` returns:

    .. math::

        rate \\cdot previous\\_value + variable + noise \\sqrt{time\\_step\\_size}

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `rate <AdaptiveIntegrator.rate>`
    | *ADDITIVE_PARAM:* `offset <AdaptiveIntegrator.offset>`
    |

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for the value to be integrated;  if it is a list or array, each element is independently
        integrated.

    rate : float, list or 1d array : default 1.0
        specifies the value used to scale the contribution of `previous_value <LeakyCompetingIntegrator.previous_value>`
        to the integral on each time step.  If it is a list or array, it must be the same length as `variable
        <ConstantIntegrator.variable>` (see `rate <LeakyCompetingIntegrator.rate>` for details).

    noise : float, function, list or 1d array : default 0.0
        specifies random value added to integral in each call to `function <LeakyCompetingIntegrator.function>`;
        if it is a list or array, it must be the same length as `variable <LeakyCompetingIntegrator.variable>`
        (see `noise <Integrator_Noise>` for additonal details).

    offset : float, list or 1d array : default 0.0
        specifies a constant value added to integral in each call to `function <LeakyCompetingIntegrator.function>`;
        if it is a list or array, it must be the same length as `variable <LeakyCompetingIntegrator.variable>`
        (see `offset <LeakyCompetingIntegrator.offset>` for details).

    time_step_size : float : default 0.0
        determines the timing precision of the integration process (see `time_step_size
        <LeakyCompetingIntegrator.time_step_size>` for details.

    initializer : float, list or 1d array : default 0.0
        specifies starting value(s) for integration.  If it is a list or array, it must be the same length as
        `default_variable <default_variable.variable>` (see `initializer <Integrator_Initializer>`
        for details).

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        current input value some portion of which (determined by `rate <LeakyCompetingIntegrator.rate>`) will be
        added to the prior value;  if it is an array, each element is independently integrated.

    rate : float or 1d array
        scales the contribution of `previous_value <LeakyCompetingIntegrator.previous_value>` to the accumulation of
        the `value <LeakyCompetingIntegrator.value>` on each time step. If it is a float or has a single element,
        its value is applied to all the elements of `previous_value <LeakyCompetingIntegrator.previous_value>`; if it
        is an array, each element is applied to the corresponding element of `previous_value
        <LeakyCompetingIntegrator.previous_value>`.  Serves as *MULTIPLICATIVE_PARAM*  for `modulation
        <ModulatorySignal_Modulation>` of `function <LeakyCompetingIntegrator.function>`.

    noise : float, Function, or 1d array
        random value added to integral in each call to `function <LeakyCompetingIntegrator.function>`.
        (see `noise <Integrator_Noise>` for details).

    offset : float or 1d array
        constant value added to integral in each call to `function <LeakyCompetingIntegrator.function>`. If `variable
        <LeakyCompetingIntegrator.variable>` is an array and offset is a float, offset is applied to each element  of
        the integral;  if offset is a list or array, each of its elements is applied to each of the corresponding
        elements of the integral (i.e., Hadamard addition). Serves as *ADDITIVE_PARAM* for `modulation
        <ModulatorySignal_Modulation>` of `function <LeakyCompetingIntegrator.function>`.

    time_step_size : float
        determines the timing precision of the integration process and is used to scale the `noise
        <LeakyCompetingIntegrator.noise>` parameter appropriately.

    initializer : float or 1d array
        determines the starting value(s) for integration (i.e., the value(s) to which `previous_value
        <LeakyCompetingIntegrator.previous_value>` is set (see `initializer <Integrator_Initializer>` for details).

    previous_value : 1d array : default ClassDefaults.variable
        stores previous value with which `variable <LeakyCompetingIntegrator.variable>` is integrated.

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).
    """

    componentName = LEAKY_COMPETING_INTEGRATOR_FUNCTION

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                offset
                    see `offset <LeakyCompetingIntegrator.offset>`

                    :default value: None
                    :type:

                rate
                    see `rate <LeakyCompetingIntegrator.rate>`

                    :default value: 1.0
                    :type: float

                time_step_size
                    see `time_step_size <LeakyCompetingIntegrator.time_step_size>`

                    :default value: 0.1
                    :type: float

        """
        rate = Param(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        offset = Param(None, modulable=True, aliases=[ADDITIVE_PARAM])
        time_step_size = Param(0.1, modulable=True)

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        RATE: None,
        OFFSET: None,
        NOISE: None
    })

    multiplicative_param = RATE
    additive_param = OFFSET

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 rate: parameter_spec = 1.0,
                 noise=0.0,
                 offset=None,
                 time_step_size=0.1,
                 initializer=None,
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None):

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(rate=rate,
                                                  noise=noise,
                                                  offset=offset,
                                                  time_step_size=time_step_size,
                                                  initializer=initializer,
                                                  params=params)

        super().__init__(
            default_variable=default_variable,
            initializer=initializer,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

        self.has_initializers = True

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """

        Arguments
        ---------

        variable : number, list or array : default ClassDefaults.variable
           a single value or array of values to be integrated.

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.

        Returns
        -------

        updated value of integral : 2d array

        """

        variable = self._check_args(variable=variable, execution_id=execution_id, params=params, context=context)

        rate = np.atleast_1d(self.get_current_function_param(RATE, execution_id))
        initializer = self.get_current_function_param(INITIALIZER, execution_id)  # unnecessary?
        time_step_size = self.get_current_function_param(TIME_STEP_SIZE, execution_id)
        offset = self.get_current_function_param(OFFSET, execution_id)

        if offset is None:
            offset = 0.0

        # execute noise if it is a function
        noise = self._try_execute_param(self.get_current_function_param(NOISE, execution_id), variable)
        previous_value = self.get_previous_value(execution_id)
        new_value = variable

        # Gilzenrat: previous_value + (-previous_value + variable)*self.time_step_size + noise --> rate = -1
        value = previous_value + (rate * previous_value + new_value) * time_step_size + noise * (time_step_size ** 0.5)

        adjusted_value = value + offset

        # If this NOT an initialization run, update the old value
        # If it IS an initialization run, leave as is
        #    (don't want to count it as an execution step)
        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            self.parameters.previous_value.set(adjusted_value, execution_id)

        return self.convert_output_type(adjusted_value)


class FitzHughNagumoIntegrator(IntegratorFunction):  # ----------------------------------------------------------------------------
    """
    FitzHughNagumoIntegrator(                      \
        default_variable=1.0,           \
        initial_w=0.0,                  \
        initial_v=0.0,                  \
        time_step_size=0.05,            \
        t_0=0.0,                        \
        a_v=-1/3,                       \
        b_v=0.0,                        \
        c_v=1.0,                        \
        d_v=0.0,                        \
        e_v=-1.0,                       \
        f_v=1.0,                        \
        threshold=-1.0                  \
        time_constant_v=1.0,            \
        a_w=1.0,                        \
        b_w=-0.8,                       \
        c_w=0.7,                        \
        mode=1.0,                       \
        uncorrelated_activity=0.0       \
        time_constant_w = 12.5,         \
        integration_method="RK4"        \
        params=None,                    \
        owner=None,                     \
        prefs=None,                     \
        )

    .. _FitzHughNagumoIntegrator:

    `function <FitzHughNagumoIntegrator.function>` returns one time step of integration of the `Fitzhugh-Nagumo model
    https://en.wikipedia.org/wiki/FitzHugh–Nagumo_model>`_ of an excitable oscillator:

    .. math::
            time\\_constant_v \\frac{dv}{dt} = a_v * v^3 + (1 + threshold) * b_v * v^2 + (- threshold) * c_v * v^2 +
            d_v + e_v * w + f_v * I_{ext}

    where
    .. math::
            time\\_constant_w * \\frac{dw}{dt} =` mode * a_w * v + b_w * w +c_w + (1 - mode) * uncorrelated\\_activity

    Either `Euler <https://en.wikipedia.org/wiki/Euler_method>`_ or `Dormand–Prince (4th Order Runge-Kutta)
    <https://en.wikipedia.org/wiki/Dormand–Prince_method>`_ methods of numerical integration can be used.

    The FitzHughNagumoIntegrator implements all of the parameters of the FitzHughNagumo model; however, not all combinations of
    these are sensible. Typically, they are combined into two sets.  These are described below, followed by
    a describption of how they are used to implement three common variants of the model with the FitzHughNagumoIntegrator.

    Parameter Sets
    ^^^^^^^^^^^^^^

    **Fast, Excitatory Variable:**

    .. math::
       \\frac{dv}{dt} = \\frac{a_v v^{3} + b_v v^{2} (1+threshold) - c_v v\\, threshold + d_v + e_v\\, previous_w +
       f_v\\, variable)}{time\\, constant_v}


    **Slow, Inactivating Variable:**

    .. math::
       \\frac{dw}{dt} = \\frac{a_w\\, mode\\, previous_v + b_w w + c_w + uncorrelated\\,activity\\,(1-mode)}{time\\,
       constant_w}

    Three Common Variants
    ^^^^^^^^^^^^^^^^^^^^^

    (1) **Fitzhugh-Nagumo Model**

        **Fast, Excitatory Variable:**

        .. math::
            \\frac{dv}{dt} = v - \\frac{v^3}{3} - w + I_{ext}

        **Slow, Inactivating Variable:**

        .. math::
            \\frac{dw}{dt} = \\frac{v + a - bw}{T}

        :math:`\\frac{dw}{dt}` often has the following parameter values:

        .. math::
            \\frac{dw}{dt} = 0.08\\,(v + 0.7 - 0.8 w)

        **Implementation in FitzHughNagumoIntegrator**

        The default values implement the above equations.


    (2) **Modified FitzHughNagumo Model**

        **Fast, Excitatory Variable:**

        .. math::
            \\frac{dv}{dt} = v(a-v)(v-1) - w + I_{ext}

        **Slow, Inactivating Variable:**

        .. math::
            \\frac{dw}{dt} = bv - cw

        `Mahbub Khan (2013) <http://pcwww.liv.ac.uk/~bnvasiev/Past%20students/Mahbub_549.pdf>`_ provides a nice summary
        of why this formulation is useful.

        **Implementation in FitzHughNagumoIntegrator**

            The following parameter values must be specified in the equation for :math:`\\frac{dv}{dt}`:

            +---------------------------+-----+-----+-----+-----+-----+-----+---------------+
            |**FitzHughNagumoIntegrator Parameter**| a_v | b_v | c_v | d_v | e_v | f_v |time_constant_v|
            +---------------------------+-----+-----+-----+-----+-----+-----+---------------+
            |**Value**                  |-1.0 |1.0  |1.0  |0.0  |-1.0 |1.0  |1.0            |
            +---------------------------+-----+-----+-----+-----+-----+-----+---------------+

            When the parameters above are set to the listed values, the FitzHughNagumoIntegrator equation for :math:`\\frac{dv}{dt}`
            reduces to the Modified FitzHughNagumo formulation, and the remaining parameters in the :math:`\\frac{dv}{dt}` equation
            correspond as follows:

            +-----------------------------+---------------------------------------+------------------------------------+
            |**FitzHughNagumoIntegrator Parameter**  |`threshold <FitzHughNagumoIntegrator.threshold>`  |`variable <FitzHughNagumoIntegrator.variable>` |
            +-----------------------------+---------------------------------------+------------------------------------+
            |**Modified FitzHughNagumo Parameter**   |a                                      |:math:`I_{ext}`                     |
            +-----------------------------+---------------------------------------+------------------------------------+

            Te following parameter values must be set in the equation for :math:`\\frac{dw}{dt}`:

            +----------------------------+-----+------+- ---------------+-----------------------+
            |**FitzHughNagumoIntegrator Parameter** |c_w  | mode | time_constant_w | uncorrelated_activity |
            +----------------------------+-----+------+- ---------------+-----------------------+
            |**Value**                   | 0.0 | 1.0  | 1.0             |  0.0                  |
            +----------------------------+-----+------+- ---------------+-----------------------+

            When the parameters above are set to the listed values, the FitzHughNagumoIntegrator equation for :math:`\\frac{dw}{dt}`
            reduces to the Modified FitzHughNagumo formulation, and the remaining parameters in the :math:`\\frac{dw}{dt}` equation
            correspond as follows:

            +------------------------------+----------------------------+-------------------------------------+
            |**FitzHughNagumoIntegrator Parameter**   |`a_w <FitzHughNagumoIntegrator.a_w>`   |*NEGATIVE* `b_w <FitzHughNagumoIntegrator.b_w>` |
            +------------------------------+----------------------------+-------------------------------------+
            |**Modified FitzHughNagumo Parameter**    |b                           |c                                    |
            +------------------------------+----------------------------+-------------------------------------+

    (3) **Modified FitzHughNagumo Model as implemented in** `Gilzenrat (2002) <http://www.sciencedirect.com/science/article/pii/S0893608002000552?via%3Dihub>`_

        **Fast, Excitatory Variable:**

        [Eq. (6) in `Gilzenrat (2002) <http://www.sciencedirect.com/science/article/pii/S0893608002000552?via%3Dihub>`_ ]

        .. math::

            \\tau_v \\frac{dv}{dt} = v(a-v)(v-1) - u + w_{vX_1}\\, f(X_1)

        **Slow, Inactivating Variable:**

        [Eq. (7) & Eq. (8) in `Gilzenrat (2002) <http://www.sciencedirect.com/science/article/pii/S0893608002000552?via%3Dihub>`_ ]

        .. math::

            \\tau_u \\frac{du}{dt} = Cv + (1-C)\\, d - u

        **Implementation in FitzHughNagumoIntegrator**

            The following FitzHughNagumoIntegrator parameter values must be set in the equation for :math:`\\frac{dv}{dt}`:

            +---------------------------+-----+-----+-----+-----+-----+
            |**FitzHughNagumoIntegrator Parameter**| a_v | b_v | c_v | d_v | e_v |
            +---------------------------+-----+-----+-----+-----+-----+
            |**Value**                  |-1.0 |1.0  |1.0  |0.0  |-1.0 |
            +---------------------------+-----+-----+-----+-----+-----+

            When the parameters above are set to the listed values, the FitzHughNagumoIntegrator equation for :math:`\\frac{dv}{dt}`
            reduces to the Gilzenrat formulation, and the remaining parameters in the :math:`\\frac{dv}{dt}` equation
            correspond as follows:

            +----------------------------+-------------------------------------+-----------------------------------+-------------------------+----------------------------------------------------+
            |**FitzHughNagumoIntegrator Parameter** |`threshold <FitzHughNagumoIntegrator.threshold>`|`variable <FitzHughNagumoIntegrator.variable>`|`f_v <FitzHughNagumoIntegrator.f_v>`|`time_constant_v <FitzHughNagumoIntegrator.time_constant_v>`   |
            +----------------------------+-------------------------------------+-----------------------------------+-------------------------+----------------------------------------------------+
            |**Gilzenrat Parameter**     |a                                    |:math:`f(X_1)`                     |:math:`w_{vX_1}`         |:math:`T_{v}`                                       |
            +----------------------------+-------------------------------------+-----------------------------------+-------------------------+----------------------------------------------------+

            The following FitzHughNagumoIntegrator parameter values must be set in the equation for :math:`\\frac{dw}{dt}`:

            +----------------------------+-----+-----+-----+
            |**FitzHughNagumoIntegrator Parameter** | a_w | b_w | c_w |
            +----------------------------+-----+-----+-----+
            |**Value**                   | 1.0 |-1.0 |0.0  |
            +----------------------------+-----+-----+-----+

            When the parameters above are set to the listed values, the FitzHughNagumoIntegrator equation for
            :math:`\\frac{dw}{dt}` reduces to the Gilzenrat formulation, and the remaining parameters in the
            :math:`\\frac{dw}{dt}` equation correspond as follows:

            +-----------------------------+-----------------------------+-------------------------------------------------------------+----------------------------------------------------+
            |**FitzHughNagumoIntegrator Parameter**  |`mode <FitzHughNagumoIntegrator.mode>`  |`uncorrelated_activity <FitzHughNagumoIntegrator.uncorrelated_activity>`|`time_constant_v <FitzHughNagumoIntegrator.time_constant_w>`   |
            +-----------------------------+-----------------------------+-------------------------------------------------------------+----------------------------------------------------+
            |**Gilzenrat Parameter**      |C                            |d                                                            |:math:`T_{u}`                                       |
            +-----------------------------+-----------------------------+-------------------------------------------------------------+----------------------------------------------------+

    Arguments
    ---------

    default_variable : number, list or array : default ClassDefaults.variable
        specifies a template for the external stimulus

    initial_w : float, list or 1d array : default 0.0
        specifies starting value for integration of dw/dt.  If it is a list or array, it must be the same length as
        `default_variable <FitzHughNagumoIntegrator.variable>`

    initial_v : float, list or 1d array : default 0.0
        specifies starting value for integration of dv/dt.  If it is a list or array, it must be the same length as
        `default_variable <FitzHughNagumoIntegrator.variable>`

    time_step_size : float : default 0.1
        specifies the time step size of numerical integration

    t_0 : float : default 0.0
        specifies starting value for time

    a_v : float : default -1/3
        coefficient on the v^3 term of the dv/dt equation

    b_v : float : default 0.0
        coefficient on the v^2 term of the dv/dt equation

    c_v : float : default 1.0
        coefficient on the v term of the dv/dt equation

    d_v : float : default 0.0
        constant term in the dv/dt equation

    e_v : float : default -1.0
        coefficient on the w term in the dv/dt equation

    f_v : float : default  1.0
        coefficient on the external stimulus (`variable <FitzHughNagumoIntegrator.variable>`) term in the dv/dt equation

    time_constant_v : float : default 1.0
        scaling factor on the dv/dt equation

    a_w : float : default 1.0,
        coefficient on the v term of the dw/dt equation

    b_w : float : default -0.8,
        coefficient on the w term of the dv/dt equation

    c_w : float : default 0.7,
        constant term in the dw/dt equation

    threshold : float : default -1.0
        specifies a value of the input below which the LC will tend not to respond and above which it will

    mode : float : default 1.0
        coefficient which simulates electrotonic coupling by scaling the values of dw/dt such that the v term
        (representing the input from the LC) increases when the uncorrelated_activity term (representing baseline
        activity) decreases

    uncorrelated_activity : float : default 0.0
        constant term in the dw/dt equation

    time_constant_w : float : default 12.5
        scaling factor on the dv/dt equation

    integration_method: str : default "RK4"
        selects the numerical integration method. Currently, the choices are: "RK4" (4th Order Runge-Kutta) or "EULER"
        (Forward Euler)

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    variable : number or array
        External stimulus

    previous_v : 1d array : default ClassDefaults.variable
        stores accumulated value of v during integration

    previous_w : 1d array : default ClassDefaults.variable
        stores accumulated value of w during integration

    previous_t : float
        stores accumulated value of time, which is incremented by time_step_size on each execution of the function

    owner : Component
        `component <Component>` to which the Function has been assigned.

    initial_w : float, list or 1d array : default 0.0
        specifies starting value for integration of dw/dt.  If it is a list or array, it must be the same length as
        `default_variable <FitzHughNagumoIntegrator.variable>`

    initial_v : float, list or 1d array : default 0.0
        specifies starting value for integration of dv/dt.  If it is a list or array, it must be the same length as
        `default_variable <FitzHughNagumoIntegrator.variable>`

    time_step_size : float : default 0.1
        specifies the time step size of numerical integration

    t_0 : float : default 0.0
        specifies starting value for time

    a_v : float : default -1/3
        coefficient on the v^3 term of the dv/dt equation

    b_v : float : default 0.0
        coefficient on the v^2 term of the dv/dt equation

    c_v : float : default 1.0
        coefficient on the v term of the dv/dt equation

    d_v : float : default 0.0
        constant term in the dv/dt equation

    e_v : float : default -1.0
        coefficient on the w term in the dv/dt equation

    f_v : float : default  1.0
        coefficient on the external stimulus (`variable <FitzHughNagumoIntegrator.variable>`) term in the dv/dt equation

    time_constant_v : float : default 1.0
        scaling factor on the dv/dt equation

    a_w : float : default 1.0
        coefficient on the v term of the dw/dt equation

    b_w : float : default -0.8
        coefficient on the w term of the dv/dt equation

    c_w : float : default 0.7
        constant term in the dw/dt equation

    threshold : float : default -1.0
        coefficient that scales both the v^2 [ (1+threshold)*v^2 ] and v [ (-threshold)*v ] terms in the dv/dt equation
        under a specific formulation of the FitzHughNagumo equations, the threshold parameter behaves as a "threshold of
        excitation", and has the following relationship with variable (the external stimulus):

            - when the external stimulus is below the threshold of excitation, the system is either in a stable state,
              or will emit a single excitation spike, then reach a stable state. The behavior varies depending on the
              magnitude of the difference between the threshold and the stimulus.

            - when the external stimulus is equal to or above the threshold of excitation, the system is
              unstable, and will emit many excitation spikes

            - when the external stimulus is too far above the threshold of excitation, the system will emit some
              excitation spikes before reaching a stable state.

    mode : float : default 1.0
        coefficient which simulates electrotonic coupling by scaling the values of dw/dt such that the v term
        (representing the input from the LC) increases when the uncorrelated_activity term (representing baseline
        activity) decreases

    uncorrelated_activity : float : default 0.0
        constant term in the dw/dt equation

    time_constant_w : float : default 12.5
        scaling factor on the dv/dt equation

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).
    """

    componentName = FITZHUGHNAGUMO_INTEGRATOR_FUNCTION

    class Params(IntegratorFunction.Params):
        """
            Attributes
            ----------

                variable
                    see `variable <FitzHughNagumoIntegrator.variable>`

                    :default value: numpy.array([1.])
                    :type: numpy.ndarray
                    :read only: True

                a_v
                    see `a_v <FitzHughNagumoIntegrator.a_v>`

                    :default value: 0.3333333333333333
                    :type: float

                a_w
                    see `a_w <FitzHughNagumoIntegrator.a_w>`

                    :default value: 1.0
                    :type: float

                b_v
                    see `b_v <FitzHughNagumoIntegrator.b_v>`

                    :default value: 0.0
                    :type: float

                b_w
                    see `b_w <FitzHughNagumoIntegrator.b_w>`

                    :default value: -0.8
                    :type: float

                c_v
                    see `c_v <FitzHughNagumoIntegrator.c_v>`

                    :default value: 1.0
                    :type: float

                c_w
                    see `c_w <FitzHughNagumoIntegrator.c_w>`

                    :default value: 0.7
                    :type: float

                d_v
                    see `d_v <FitzHughNagumoIntegrator.d_v>`

                    :default value: 0.0
                    :type: float

                e_v
                    see `e_v <FitzHughNagumoIntegrator.e_v>`

                    :default value: -1.0
                    :type: float

                f_v
                    see `f_v <FitzHughNagumoIntegrator.f_v>`

                    :default value: 1.0
                    :type: float

                initial_v
                    see `initial_v <FitzHughNagumoIntegrator.initial_v>`

                    :default value: numpy.array([1.])
                    :type: numpy.ndarray

                initial_w
                    see `initial_w <FitzHughNagumoIntegrator.initial_w>`

                    :default value: numpy.array([1.])
                    :type: numpy.ndarray

                integration_method
                    see `integration_method <FitzHughNagumoIntegrator.integration_method>`

                    :default value: `RK4`
                    :type: str

                mode
                    see `mode <FitzHughNagumoIntegrator.mode>`

                    :default value: 1.0
                    :type: float

                previous_time
                    see `previous_time <FitzHughNagumoIntegrator.previous_time>`

                    :default value: 0.0
                    :type: float

                previous_v
                    see `previous_v <FitzHughNagumoIntegrator.previous_v>`

                    :default value: numpy.array([1.])
                    :type: numpy.ndarray

                previous_w
                    see `previous_w <FitzHughNagumoIntegrator.previous_w>`

                    :default value: numpy.array([1.])
                    :type: numpy.ndarray

                t_0
                    see `t_0 <FitzHughNagumoIntegrator.t_0>`

                    :default value: 0.0
                    :type: float

                threshold
                    see `threshold <FitzHughNagumoIntegrator.threshold>`

                    :default value: -1.0
                    :type: float

                time_constant_v
                    see `time_constant_v <FitzHughNagumoIntegrator.time_constant_v>`

                    :default value: 1.0
                    :type: float

                time_constant_w
                    see `time_constant_w <FitzHughNagumoIntegrator.time_constant_w>`

                    :default value: 12.5
                    :type: float

                time_step_size
                    see `time_step_size <FitzHughNagumoIntegrator.time_step_size>`

                    :default value: 0.05
                    :type: float

                uncorrelated_activity
                    see `uncorrelated_activity <FitzHughNagumoIntegrator.uncorrelated_activity>`

                    :default value: 0.0
                    :type: float

        """
        variable = Param(np.array([1.0]), read_only=True)
        time_step_size = Param(0.05, modulable=True)
        a_v = Param(1.0 / 3, modulable=True)
        b_v = Param(0.0, modulable=True)
        c_v = Param(1.0, modulable=True)
        d_v = Param(0.0, modulable=True)
        e_v = Param(-1.0, modulable=True)
        f_v = Param(1.0, modulable=True)
        time_constant_v = Param(1.0, modulable=True)
        a_w = Param(1.0, modulable=True)
        b_w = Param(-0.8, modulable=True)
        c_w = Param(0.7, modulable=True)
        threshold = Param(-1.0, modulable=True)
        time_constant_w = Param(12.5, modulable=True)
        mode = Param(1.0, modulable=True)
        uncorrelated_activity = Param(0.0, modulable=True)

        # FIX: make an integration_method enum class for RK4/EULER
        integration_method = Param("RK4", stateful=False)

        initial_w = np.array([1.0])
        initial_v = np.array([1.0])
        t_0 = 0.0
        previous_w = np.array([1.0])
        previous_v = np.array([1.0])
        previous_time = 0.0

    paramClassDefaults = Function_Base.paramClassDefaults.copy()
    paramClassDefaults.update({
        NOISE: None,
        INCREMENT: None,
    })

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 # scale=1.0,
                 # offset=0.0,
                 initial_w=0.0,
                 initial_v=0.0,
                 a_v=-1 / 3,
                 b_v=0.0,
                 c_v=1.0,
                 d_v=0.0,
                 e_v=-1.0,
                 f_v=1.0,
                 time_constant_v=1.0,
                 a_w=1.0,
                 b_w=-0.8,
                 c_w=0.7,
                 time_constant_w=12.5,
                 t_0=0.0,
                 threshold=-1.0,
                 time_step_size=0.05,
                 mode=1.0,
                 uncorrelated_activity=0.0,
                 integration_method="RK4",
                 params: tc.optional(dict) = None,
                 owner=None,
                 prefs: is_pref_set = None,
                 **kwargs):

        # These may be passed (as standard IntegratorFunction args) but are not used by FitzHughNagumo
        unsupported_args = {NOISE, INITIALIZER, RATE, OFFSET}
        if any(k in unsupported_args for k in kwargs):
            s = 's' if len(kwargs)>1 else ''
            warnings.warn("{} arg{} not supported in {}".
                          format(repr(", ".join(list(kwargs.keys()))),s, self.__class__.__name__))
            for k in unsupported_args:
                if k in kwargs:
                    del kwargs[k]

        if not hasattr(self, "initializers"):
            self.initializers = ["initial_v", "initial_w", "t_0"]

        if not hasattr(self, "stateful_attributes"):
            self.stateful_attributes = ["previous_v", "previous_w", "previous_time"]

        # Assign args to params and functionParams dicts (kwConstants must == arg names)
        params = self._assign_args_to_param_dicts(default_variable=default_variable,
                                                  initial_v=initial_v,
                                                  initial_w=initial_w,
                                                  time_step_size=time_step_size,
                                                  t_0=t_0,
                                                  a_v=a_v,
                                                  b_v=b_v,
                                                  c_v=c_v,
                                                  d_v=d_v,
                                                  e_v=e_v,
                                                  f_v=f_v,
                                                  time_constant_v=time_constant_v,
                                                  a_w=a_w,
                                                  b_w=b_w,
                                                  c_w=c_w,
                                                  threshold=threshold,
                                                  mode=mode,
                                                  uncorrelated_activity=uncorrelated_activity,
                                                  integration_method=integration_method,
                                                  time_constant_w=time_constant_w,
                                                  params=params,
                                                  )

        super().__init__(
            default_variable=default_variable,
            params=params,
            owner=owner,
            prefs=prefs,
            context=ContextFlags.CONSTRUCTOR)

    @property
    def output_type(self):
        return self._output_type

    @output_type.setter
    def output_type(self, value):
        # disabled because it happens during normal execution, may be confusing
        # warnings.warn('output_type conversion disabled for {0}'.format(self.__class__.__name__))
        self._output_type = None

    def _validate_params(self, request_set, target_set=None, context=None):
        super()._validate_params(request_set=request_set,
                                 target_set=target_set,
                                 context=context)
        if self.integration_method not in {"RK4", "EULER"}:
            raise FunctionError("Invalid integration method ({}) selected for {}. Choose 'RK4' or 'EULER'".
                                format(self.integration_method, self.name))

    def _euler_FitzHughNagumo(
        self, variable, previous_value_v, previous_value_w, previous_time, slope_v, slope_w, time_step_size,
        a_v,
        threshold, b_v, c_v, d_v, e_v, f_v, time_constant_v, mode, a_w, b_w, c_w, uncorrelated_activity,
        time_constant_w, execution_id=None
    ):

        slope_v_approx = slope_v(
            variable,
            previous_time,
            previous_value_v,
            previous_value_w,
            a_v,
            threshold,
            b_v,
            c_v,
            d_v,
            e_v,
            f_v,
            time_constant_v,
            execution_id=execution_id
        )

        slope_w_approx = slope_w(
            variable,
            previous_time,
            previous_value_w,
            previous_value_v,
            mode,
            a_w,
            b_w,
            c_w,
            uncorrelated_activity,
            time_constant_w,
            execution_id=execution_id
        )

        new_v = previous_value_v + time_step_size * slope_v_approx
        new_w = previous_value_w + time_step_size * slope_w_approx

        return new_v, new_w

    def _runge_kutta_4_FitzHughNagumo(
        self, variable, previous_value_v, previous_value_w, previous_time, slope_v, slope_w,
        time_step_size,
        a_v, threshold, b_v, c_v, d_v, e_v, f_v, time_constant_v, mode, a_w, b_w, c_w,
        uncorrelated_activity, time_constant_w, execution_id=None
    ):

        # First approximation
        # v is approximately previous_value_v
        # w is approximately previous_value_w

        slope_v_approx_1 = slope_v(
            variable,
            previous_time,
            previous_value_v,
            previous_value_w,
            a_v,
            threshold,
            b_v,
            c_v,
            d_v,
            e_v,
            f_v,
            time_constant_v,
            execution_id=execution_id
        )

        slope_w_approx_1 = slope_w(
            variable,
            previous_time,
            previous_value_w,
            previous_value_v,
            mode,
            a_w,
            b_w,
            c_w,
            uncorrelated_activity,
            time_constant_w,
            execution_id=execution_id
        )
        # Second approximation
        # v is approximately previous_value_v + 0.5 * time_step_size * slope_w_approx_1
        # w is approximately previous_value_w + 0.5 * time_step_size * slope_w_approx_1

        slope_v_approx_2 = slope_v(
            variable,
            previous_time + time_step_size / 2,
            previous_value_v + (0.5 * time_step_size * slope_v_approx_1),
            previous_value_w + (0.5 * time_step_size * slope_w_approx_1),
            a_v,
            threshold,
            b_v,
            c_v,
            d_v,
            e_v,
            f_v,
            time_constant_v,
            execution_id=execution_id
        )

        slope_w_approx_2 = slope_w(
            variable,
            previous_time + time_step_size / 2,
            previous_value_w + (0.5 * time_step_size * slope_w_approx_1),
            previous_value_v + (0.5 * time_step_size * slope_v_approx_1),
            mode,
            a_w,
            b_w,
            c_w,
            uncorrelated_activity,
            time_constant_w,
            execution_id=execution_id
        )

        # Third approximation
        # v is approximately previous_value_v + 0.5 * time_step_size * slope_v_approx_2
        # w is approximately previous_value_w + 0.5 * time_step_size * slope_w_approx_2

        slope_v_approx_3 = slope_v(
            variable,
            previous_time + time_step_size / 2,
            previous_value_v + (0.5 * time_step_size * slope_v_approx_2),
            previous_value_w + (0.5 * time_step_size * slope_w_approx_2),
            a_v,
            threshold,
            b_v,
            c_v,
            d_v,
            e_v,
            f_v,
            time_constant_v,
            execution_id=execution_id
        )

        slope_w_approx_3 = slope_w(
            variable,
            previous_time + time_step_size / 2,
            previous_value_w + (0.5 * time_step_size * slope_w_approx_2),
            previous_value_v + (0.5 * time_step_size * slope_v_approx_2),
            mode,
            a_w,
            b_w,
            c_w,
            uncorrelated_activity,
            time_constant_w,
            execution_id=execution_id
        )
        # Fourth approximation
        # v is approximately previous_value_v + time_step_size * slope_v_approx_3
        # w is approximately previous_value_w + time_step_size * slope_w_approx_3

        slope_v_approx_4 = slope_v(
            variable,
            previous_time + time_step_size,
            previous_value_v + (time_step_size * slope_v_approx_3),
            previous_value_w + (time_step_size * slope_w_approx_3),
            a_v,
            threshold,
            b_v,
            c_v,
            d_v,
            e_v,
            f_v,
            time_constant_v,
            execution_id=execution_id
        )

        slope_w_approx_4 = slope_w(
            variable,
            previous_time + time_step_size,
            previous_value_w + (time_step_size * slope_w_approx_3),
            previous_value_v + (time_step_size * slope_v_approx_3),
            mode,
            a_w,
            b_w,
            c_w,
            uncorrelated_activity,
            time_constant_w,
            execution_id=execution_id
        )

        new_v = previous_value_v \
                + (time_step_size / 6) * (
        slope_v_approx_1 + 2 * (slope_v_approx_2 + slope_v_approx_3) + slope_v_approx_4)
        new_w = previous_value_w \
                + (time_step_size / 6) * (
        slope_w_approx_1 + 2 * (slope_w_approx_2 + slope_w_approx_3) + slope_w_approx_4)

        return new_v, new_w

    def dv_dt(self, variable, time, v, w, a_v, threshold, b_v, c_v, d_v, e_v, f_v, time_constant_v, execution_id=None):
        previous_w = self.get_current_function_param('previous_w', execution_id)

        val = (a_v * (v ** 3) + (1 + threshold) * b_v * (v ** 2) + (-threshold) * c_v * v + d_v
               + e_v * previous_w + f_v * variable) / time_constant_v

        # Standard coefficients - hardcoded for testing
        # val = v - (v**3)/3 - w + variable
        # Gilzenrat paper - hardcoded for testing
        # val = (v*(v-0.5)*(1-v) - w + variable)/0.01
        return val

    def dw_dt(self, variable, time, w, v, mode, a_w, b_w, c_w, uncorrelated_activity, time_constant_w, execution_id=None):
        previous_v = self.get_current_function_param('previous_v', execution_id)

        # val = np.ones_like(variable)*(mode*a_w*self.previous_v + b_w*w + c_w + (1-mode)*uncorrelated_activity)/time_constant_w
        val = (mode * a_w * previous_v + b_w * w + c_w + (1 - mode) * uncorrelated_activity) / time_constant_w

        # Standard coefficients - hardcoded for testing
        # val = (v + 0.7 - 0.8*w)/12.5
        # Gilzenrat paper - hardcoded for testing

        # val = (v - 0.5*w)
        if not np.isscalar(variable):
            val = np.broadcast_to(val, variable.shape)

        return val

    def function(self,
                 variable=None,
                 execution_id=None,
                 params=None,
                 context=None):
        """

        Arguments
        ---------

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterState_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.

        Returns
        -------

        current value of v , current value of w : float, list, or array

        """

        # FIX: SHOULDN'T THERE BE A CALL TO get_current_function_param('variable', execution_id) HERE??

        # # FIX: TEMPORARY CHECK UNTIL ARRAY IS SUPPORTED
        # if variable is not None and not np.isscalar(variable) and len(variable)>1:
        #     raise FunctionError("{} presently supports only a scalar variable".format(self.__class__.__name__))

        a_v = self.get_current_function_param("a_v", execution_id)
        b_v = self.get_current_function_param("b_v", execution_id)
        c_v = self.get_current_function_param("c_v", execution_id)
        d_v = self.get_current_function_param("d_v", execution_id)
        e_v = self.get_current_function_param("e_v", execution_id)
        f_v = self.get_current_function_param("f_v", execution_id)
        time_constant_v = self.get_current_function_param("time_constant_v", execution_id)
        threshold = self.get_current_function_param("threshold", execution_id)
        a_w = self.get_current_function_param("a_w", execution_id)
        b_w = self.get_current_function_param("b_w", execution_id)
        c_w = self.get_current_function_param("c_w", execution_id)
        uncorrelated_activity = self.get_current_function_param("uncorrelated_activity", execution_id)
        time_constant_w = self.get_current_function_param("time_constant_w", execution_id)
        mode = self.get_current_function_param("mode", execution_id)
        time_step_size = self.get_current_function_param(TIME_STEP_SIZE, execution_id)
        previous_v = self.get_current_function_param("previous_v", execution_id)
        previous_w = self.get_current_function_param("previous_w", execution_id)
        previous_time = self.get_current_function_param("previous_time", execution_id)

        # integration_method is a compile time parameter
        integration_method = self.get_current_function_param("integration_method", execution_id)
        if integration_method == "RK4":
            approximate_values = self._runge_kutta_4_FitzHughNagumo(
                variable,
                previous_v,
                previous_w,
                previous_time,
                self.dv_dt,
                self.dw_dt,
                time_step_size,
                a_v,
                threshold,
                b_v,
                c_v,
                d_v,
                e_v,
                f_v,
                time_constant_v,
                mode,
                a_w,
                b_w,
                c_w,
                uncorrelated_activity,
                time_constant_w,
                execution_id=execution_id
            )

        elif integration_method == "EULER":
            approximate_values = self._euler_FitzHughNagumo(
                variable,
                previous_v,
                previous_w,
                previous_time,
                self.dv_dt,
                self.dw_dt,
                time_step_size,
                a_v,
                threshold,
                b_v,
                c_v,
                d_v,
                e_v,
                f_v,
                time_constant_v,
                mode,
                a_w,
                b_w,
                c_w,
                uncorrelated_activity,
                time_constant_w,
                execution_id=execution_id
            )
        else:
            raise FunctionError("Invalid integration method ({}) selected for {}".
                                format(integration_method, self.name))

        if self.parameters.context.get(execution_id).initialization_status != ContextFlags.INITIALIZING:
            previous_v = approximate_values[0]
            previous_w = approximate_values[1]
            previous_time = previous_time + time_step_size
            if not np.isscalar(variable):
                previous_time = np.broadcast_to(previous_time, variable.shape).copy()

            self.parameters.previous_v.set(previous_v, execution_id)
            self.parameters.previous_w.set(previous_w, execution_id)
            self.parameters.previous_time.set(previous_time, execution_id)

        return previous_v, previous_w, previous_time

    def _gen_llvm_function_body(self, ctx, builder, params, context, arg_in, arg_out):
        zero_i32 = ctx.int32_ty(0)

        # Get rid of 2d array. When part of a Mechanism the input,
        # (and output, and context) are 2d arrays.
        arg_in = ctx.unwrap_2d_array(builder, arg_in)
        # Load context values
        prev = {}
        for idx, ctx_el in enumerate(self.stateful_attributes):
            val = builder.gep(context, [zero_i32, ctx.int32_ty(idx)])
            prev[ctx_el] = ctx.unwrap_2d_array(builder, val)

        # Output locations
        out = {}
        for idx, out_el in enumerate(('v', 'w', 'time')):
            val = builder.gep(arg_out, [zero_i32, ctx.int32_ty(idx)])
            out[out_el] = ctx.unwrap_2d_array(builder, val)

        # Load parameters
        param_vals = {}
        for p in self._get_param_ids():
            param_ptr, builder = ctx.get_param_ptr(self, builder, params, p)
            param_vals[p] = pnlvm.helpers.load_extract_scalar_array_one(
                                            builder, param_ptr)

        inner_args = {"ctx": ctx, "var_ptr": arg_in, "param_vals": param_vals,
                      "out_v": out['v'], "out_w": out['w'],
                      "out_time": out['time'],
                      "previous_v_ptr": prev['previous_v'],
                      "previous_w_ptr": prev['previous_w'],
                      "previous_time_ptr": prev['previous_time']}

        # KDM 11/7/18: since we're compiling with this set, I'm assuming it should be
        # stateless and considered an inherent feature of the function. Changing parameter
        # to stateful=False accordingly. If it should be stateful, need to pass an execution_id here
        method = self.get_current_function_param("integration_method")
        if method == "RK4":
            func = functools.partial(self.__gen_llvm_rk4_body, **inner_args)
        elif method == "EULER":
            func = functools.partial(self.__gen_llvm_euler_body, **inner_args)
        else:
            raise FunctionError("Invalid integration method ({}) selected for {}".
                                format(method, self.name))

        with pnlvm.helpers.array_ptr_loop(builder, arg_in, method + "_body") as args:
            func(*args)

        # Save context
        result = builder.load(arg_out)
        builder.store(result, context)
        return builder

    def __gen_llvm_rk4_body(self, builder, index, ctx, var_ptr, out_v, out_w, out_time, param_vals, previous_v_ptr, previous_w_ptr, previous_time_ptr):
        var = builder.load(builder.gep(var_ptr, [ctx.int32_ty(0), index]))

        previous_v = builder.load(builder.gep(previous_v_ptr, [ctx.int32_ty(0), index]))
        previous_w = builder.load(builder.gep(previous_w_ptr, [ctx.int32_ty(0), index]))
        previous_time = builder.load(builder.gep(previous_time_ptr, [ctx.int32_ty(0), index]))

        out_v_ptr = builder.gep(out_v, [ctx.int32_ty(0), index])
        out_w_ptr = builder.gep(out_w, [ctx.int32_ty(0), index])
        out_time_ptr = builder.gep(out_time, [ctx.int32_ty(0), index])

        time_step_size = param_vals[TIME_STEP_SIZE]

        # Save output time
        time = builder.fadd(previous_time, time_step_size)
        builder.store(time, out_time_ptr)

        # First approximation uses previous_v
        input_v = previous_v
        slope_v_approx_1 = self.__gen_llvm_dv_dt(builder, ctx, var, input_v, previous_w, param_vals)

        # First approximation uses previous_w
        input_w = previous_w
        slope_w_approx_1 = self.__gen_llvm_dw_dt(builder, ctx, input_w, previous_v, param_vals)

        # Second approximation
        # v is approximately previous_value_v + 0.5 * time_step_size * slope_v_approx_1
        input_v = builder.fmul(ctx.float_ty(0.5), time_step_size)
        input_v = builder.fmul(input_v, slope_v_approx_1)
        input_v = builder.fadd(input_v, previous_v)
        slope_v_approx_2 = self.__gen_llvm_dv_dt(builder, ctx, var, input_v, previous_w, param_vals)

        # w is approximately previous_value_w + 0.5 * time_step_size * slope_w_approx_1
        input_w = builder.fmul(ctx.float_ty(0.5), time_step_size)
        input_w = builder.fmul(input_w, slope_w_approx_1)
        input_w = builder.fadd(input_w, previous_w)
        slope_w_approx_2 = self.__gen_llvm_dw_dt(builder, ctx, input_w, previous_v, param_vals)

        # Third approximation
        # v is approximately previous_value_v + 0.5 * time_step_size * slope_v_approx_2
        input_v = builder.fmul(ctx.float_ty(0.5), time_step_size)
        input_v = builder.fmul(input_v, slope_v_approx_2)
        input_v = builder.fadd(input_v, previous_v)
        slope_v_approx_3 = self.__gen_llvm_dv_dt(builder, ctx, var, input_v, previous_w, param_vals)

        # w is approximately previous_value_w + 0.5 * time_step_size * slope_w_approx_2
        input_w = builder.fmul(ctx.float_ty(0.5), time_step_size)
        input_w = builder.fmul(input_w, slope_w_approx_2)
        input_w = builder.fadd(input_w, previous_w)
        slope_w_approx_3 = self.__gen_llvm_dw_dt(builder, ctx, input_w, previous_v, param_vals)

        # Fourth approximation
        # v is approximately previous_value_v + time_step_size * slope_v_approx_3
        input_v = builder.fmul(time_step_size, slope_v_approx_3)
        input_v = builder.fadd(input_v, previous_v)
        slope_v_approx_4 = self.__gen_llvm_dv_dt(builder, ctx, var, input_v, previous_w, param_vals)

        # w is approximately previous_value_w + time_step_size * slope_w_approx_3
        input_w = builder.fmul(time_step_size, slope_w_approx_3)
        input_w = builder.fadd(input_w, previous_w)
        slope_w_approx_4 = self.__gen_llvm_dw_dt(builder, ctx, input_w, previous_v, param_vals)

        ts = builder.fdiv(time_step_size, ctx.float_ty(6.0))
        # new_v = previous_value_v \
        #    + (time_step_size/6) * (slope_v_approx_1
        #    + 2 * (slope_v_approx_2 + slope_v_approx_3) + slope_v_approx_4)
        new_v = builder.fadd(slope_v_approx_2, slope_v_approx_3)
        new_v = builder.fmul(new_v, ctx.float_ty(2.0))
        new_v = builder.fadd(new_v, slope_v_approx_1)
        new_v = builder.fadd(new_v, slope_v_approx_4)
        new_v = builder.fmul(new_v, ts)
        new_v = builder.fadd(new_v, previous_v)
        builder.store(new_v, out_v_ptr)

        # new_w = previous_walue_w \
        #    + (time_step_size/6) * (slope_w_approx_1
        #    + 2 * (slope_w_approx_2 + slope_w_approx_3) + slope_w_approx_4)
        new_w = builder.fadd(slope_w_approx_2, slope_w_approx_3)
        new_w = builder.fmul(new_w, ctx.float_ty(2.0))
        new_w = builder.fadd(new_w, slope_w_approx_1)
        new_w = builder.fadd(new_w, slope_w_approx_4)
        new_w = builder.fmul(new_w, ts)
        new_w = builder.fadd(new_w, previous_w)
        builder.store(new_w, out_w_ptr)

    def __gen_llvm_euler_body(self, builder, index, ctx, var_ptr, out_v, out_w, out_time, param_vals, previous_v_ptr, previous_w_ptr, previous_time_ptr):

        var = builder.load(builder.gep(var_ptr, [ctx.int32_ty(0), index]))
        previous_v = builder.load(builder.gep(previous_v_ptr, [ctx.int32_ty(0), index]))
        previous_w = builder.load(builder.gep(previous_w_ptr, [ctx.int32_ty(0), index]))
        previous_time = builder.load(builder.gep(previous_time_ptr, [ctx.int32_ty(0), index]))
        out_v_ptr = builder.gep(out_v, [ctx.int32_ty(0), index])
        out_w_ptr = builder.gep(out_w, [ctx.int32_ty(0), index])
        out_time_ptr = builder.gep(out_time, [ctx.int32_ty(0), index])

        time_step_size = param_vals[TIME_STEP_SIZE]

        # Save output time
        time = builder.fadd(previous_time, time_step_size)
        builder.store(time, out_time_ptr)

        # First approximation uses previous_v
        slope_v_approx = self.__gen_llvm_dv_dt(builder, ctx, var, previous_v, previous_w, param_vals)

        # First approximation uses previous_w
        slope_w_approx = self.__gen_llvm_dw_dt(builder, ctx, previous_w, previous_v, param_vals)

        # new_v = previous_value_v + time_step_size*slope_v_approx
        new_v = builder.fmul(time_step_size, slope_v_approx)
        new_v = builder.fadd(previous_v, new_v)
        builder.store(new_v, out_v_ptr)
        # new_w = previous_value_w + time_step_size*slope_w_approx
        new_w = builder.fmul(time_step_size, slope_w_approx)
        new_w = builder.fadd(previous_w, new_w)
        builder.store(new_w, out_w_ptr)

    def __gen_llvm_dv_dt(self, builder, ctx, var, v, previous_w, param_vals):
        # val = (a_v*(v**3) + (1+threshold)*b_v*(v**2) + (-threshold)*c_v*v +
        #       d_v + e_v*self.previous_w + f_v*variable)/time_constant_v
        pow_f = ctx.get_builtin("pow", [ctx.float_ty])

        v_3 = builder.call(pow_f, [v, ctx.float_ty(3.0)])
        tmp1 = builder.fmul(param_vals["a_v"], v_3)

        thr_p1 = builder.fadd(ctx.float_ty(1.0), param_vals["threshold"])
        tmp2 = builder.fmul(thr_p1, param_vals["b_v"])
        v_2 = builder.call(pow_f, [v, ctx.float_ty(2.0)])
        tmp2 = builder.fmul(tmp2, v_2)

        thr_neg = builder.fsub(ctx.float_ty(0.0), param_vals["threshold"])
        tmp3 = builder.fmul(thr_neg, param_vals["c_v"])
        tmp3 = builder.fmul(tmp3, v)

        tmp4 = param_vals["d_v"]

        tmp5 = builder.fmul(param_vals["e_v"], previous_w)

        tmp6 = builder.fmul(param_vals["f_v"], var)

        sum = ctx.float_ty(-0.0)
        sum = builder.fadd(sum, tmp1)
        sum = builder.fadd(sum, tmp2)
        sum = builder.fadd(sum, tmp3)
        sum = builder.fadd(sum, tmp4)
        sum = builder.fadd(sum, tmp5)
        sum = builder.fadd(sum, tmp6)

        res = builder.fdiv(sum, param_vals["time_constant_v"])

        return res

    def __gen_llvm_dw_dt(self, builder, ctx, w, previous_v, param_vals):
        # val = (mode*a_w*self.previous_v + b_w*w + c_w +
        #       (1-mode)*uncorrelated_activity)/time_constant_w

        tmp1 = builder.fmul(param_vals["mode"], previous_v)
        tmp1 = builder.fmul(tmp1, param_vals["a_w"])

        tmp2 = builder.fmul(param_vals["b_w"], w)

        tmp3 = param_vals["c_w"]

        mod_1 = builder.fsub(ctx.float_ty(1.0), param_vals["mode"])
        tmp4 = builder.fmul(mod_1, param_vals["uncorrelated_activity"])

        sum = ctx.float_ty(-0.0)
        sum = builder.fadd(sum, tmp1)
        sum = builder.fadd(sum, tmp2)
        sum = builder.fadd(sum, tmp3)
        sum = builder.fadd(sum, tmp4)

        res = builder.fdiv(sum, param_vals["time_constant_w"])
        return res



