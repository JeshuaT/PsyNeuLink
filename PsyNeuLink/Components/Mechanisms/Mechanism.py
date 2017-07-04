# Princeton University licenses this file to You under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may obtain a copy of the License at:
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.


# ****************************************  MECHANISM MODULE ***********************************************************

"""
..
    * :ref:`Mechanism_Overview`
    * :ref:`Mechanism_Creation`
    * :ref:`Mechanism_Structure`
     * :ref:`Mechanism_Function`
     * :ref:`Mechanism_States`
        * :ref:`Mechanism_InputStates`
        * :ref:`Mechanism_ParameterStates`
        * :ref:`Mechanism_OutputStates`
     * :ref:`Mechanism_Parameters`
     * :ref:`Mechanism_Role_In_Processes_And_Systems`
    * :ref:`Mechanism_Execution`
     * :ref:`Mechanism_Runtime_Parameters`
    * :ref:`Mechanism_Class_Reference`


.. _Mechanism_Overview:

Overview
--------

A Mechanism takes an input, transforms it in some way, and makes the result available as its output.  There are two
types of Mechanisms in PsyNeuLink:

    * `ProcessingMechanisms <ProcessingMechanism>` aggregrate the input they receive from other Mechanisms, and/or the
      input to the the `Process` or `System` to which they belong, transform it in some way, and
      provide the result as input to other Mechanisms in the Process or System, or as the output for a Process or 
      System itself.  There are a variety of different types of ProcessingMechanism, that accept various forms of
      input and transform them in different ways (see `ProcessingMechanisms <ProcessingMechanism>` for a list).
    ..
    * `AdpativeMechanisms <AdpativeMechanism>` monitor the output of one or more other Mechanisms, and use this  
      to modulate the parameters of other Mechanisms or Projections.  There are three basic AdaptiveMechanisms:
      
      * `LearningMechanisms <LearningMechanism>` - these receive training (target) values, and compare them with the 
        output of a Mechanism to generate learning signals that are used to modify 
        `MappingProjection <MappingProjections>` (see `learning <Process_Learning>`).
      
      * `ControlMechanisms <ControlMechanism>` - these evaluate the output of a specified set of Mechanisms, and 
        generate control signals used to modify the parameters of those or other Mechanisms.  
      
      * `GatingMechanisms <GatingMechanism>` - these receive input, and use this to determine whether and how to 
        modify the value of the InputState(s) and/or OutputState(s) of other Mechanisms.
      
      Each type of AdaptiveMechanism is associated with a corresponding type of Projection (`LearningProjection`,
      `ControlProjection` and `GatingProjection`, respectively).

A Mechanism is made up of four fundamental components: the function it uses to transform its input; and the States it
uses to represent its input(s), parameter(s), and output(s).

.. _Mechanism_Creation:

Creating a Mechanism
--------------------

Mechanisms can be created in several ways.  The simplest is to use the standard Python method of calling the
constructor for the desired type of Mechanism.  Alternatively, the `mechanism() <mechanism>` function can be used to
instantiate a specified type of Mechanism or a default Mechanism. Mechanisms can also be specified "in context,"
for example in the `pathway` attribute of a Process; the Mechanism can be specified in either of the ways mentioned
above, or using one of the following:

  * the name of an **existing Mechanism**;
  ..
  * the name of a **Mechanism type** (subclass);
  ..
  * a **specification dictionary** -- this can contain an entry specifying the type of Mechanism,
    and/or entries specifying the value of parameters used to instantiate it.
    These should take the following form:

      * MECHANISM_TYPE: <name of a Mechanism type>

          if this entry is absent, a `default Mechanism <LINK>` will be created.

      * <name of parameter>:<value>

          this can contain any of the standard parameters for instantiating a Mechanism
          (see `Mechanism_Parameters`) or ones specific to a particular type of Mechanism
          (see documentation for the subclass).  The key must be the name of the argument used to specify
          the parameter in the Mechanism's constructor, and the value must be a legal value for that parameter.
          The parameter values specified will be used to instantiate the Mechanism.  These can be overridden
          during execution by specifying `Mechanism_Runtime_Parameters`, either when calling the Mechanism's
          `execute <Mechanism_Base.execute>` or `run <Mechanism_Base.run>` method, or where it is
          specified in the `pathway` attribute of a `Process`.

  * **automatically** -- PsyNeuLink automatically creates one or more Mechanisms under some circumstances.
    For example, `LearningMechanisms <LearningMechanism>` (and associated `LearningProjections <LearningProjection>`)
    are created automatically when `learing <Process_Learning>` is specified for a Process.

Every Mechanism has one or more `inputStates <InputState>`, `ParameterStates <ParameterState>`, and
`outputStates <OutputState>` (summarized `below <Mechanism_States>`) that allow it to receive and send Projections,
and to execute its `function <Mechanism_Function>`).  When a Mechanism is created, it automatically creates the
ParameterStates it needs to represent its parameters, including those of its `function <Mechanism_Base.function>`.
It also creates any inputStates and outputStates required for the Projections it has been assigned. InputStates and
outputStates, and corresponding Projections, can also be specified in **input_states** and **output_state** arguments
of the Mechanism's constructor, or in its params dictionary using entries with the keys INPUT_STATES and OUTPUT_STATES, 
respectively. The value of each entry can be the name of an existing State, a specification dictionary for one, a value
(used as the State's ``variable``), a string (used to create a default State with that name), or a list containing of
any of these to create multiple States (see `InputStates <InputState_Creation>` and
`OutputStates <OutputStates_Creation>` for details).  The following is an example that creates an instance of a
TransferMechanism with a default InputState named "MY_INPUT" and three 
`pre-specified types of outputStates <OutputState_Specification>`::
 
     my_mech = TransferMechanism(input_states:['MY_INPUT'], output_states:[RESULT, MEAN, VARIANCE]) 

.. _Mechanism_Structure:

Structure
--------

.. _Mechanism_Function:

Function
~~~~~~~~

The core of every Mechanism is its function, which transforms its input to generate its output.  The function is
specified by the Mechanism's `function <Mechanism_Base.function>` attribute.  Every type of Mechanism has at least one
(primary) function, and some have additional (auxiliary) ones (for example, the `EVCMechanism <EVC_Function>`).
Mechanism functions are generally from the PsyNeuLink `Function` class.  Most Mechanisms allow their function to be
specified, using the `function` argument of the Mechanism's contructor.  The function can be specified using the name of
`Function` class, or its constructor (including arguments that specify its parameters).  For example, the
:keyword:`function` of a `TransferMechanism` can be specified to be the `Logistic` function as follows::

    my_mechanism = TransferMechanism(function=Logistic(gain=1.0, bias=-4))

Notice that the parameters of the :keyword:`function` (in this case, `gain` and `bias`) can be specified by including
them in its constructor.  Some Mechanisms support only a single function.  In that case, the :keyword:`function`
argument is not available in the Mechanism's constructor, but it does include arguments for the function's
parameters.  For example, the :keyword:`function` of a `ComparatorMechanism` is always the `LinearCombination` function,
so its constructor does not have a :keyword:`function` argument.  However, it does have a `comparison_operation`
argument, that is used to set the LinearCombination function's `operation` parameter.

For Mechanisms that offer a selection of functions, if all of the functions use the same parameters then those
parameters can also be specified as entries in a `parameter dictionary <ParameterState_Specifying_Parameters>`
used for the `params` argument of the Mechanism's constructor;  in such cases, values specified in the parameter
dictionary will override any specified within the constructor for the function itself (see `DDM_Parameters` for an
example). The parameters of a Mechanism's primary function (i.e., assigned to is `function <Mechanism_Base.function>`
attribute) are assigned to a dictionary in the Mechanism's `function_params <Mechanism_Base.function_params>`
attribute, and can be accessed using the parameter's name as the key for its entry in the dictionary.

.. _Mechanism_Custom_Function:

Any function (primary or auxiliary) used by a Mechanism can be customized by assigning a user-defined function (e.g.,
a lambda function), so long as it takes arguments and returns values that are compatible with those of the
Mechanism's default for that function. A user-defined function can be assigned using the Mechanism's `assign_params`
method (the safest means) or by assigning it directly to the corresponding attribute of the Mechanism (for its
primary function, its `function <Mechanism_Base.function>` attribute).

COMMENT:
    When a custom function is specified,
    the function itself is assigned to the Mechanism's designated attribute.  At the same time, PsyNeuLink automatically
    creates a `UserDefinedFunction` object, and assigns the custom function to its
    `function <UserDefinedFunction.function>` attribute.
COMMENT

The input to a Mechanism's `function <Mechanism_Base.function>` is provided by the Mechanism's
`variable <Mechanism_Base.variable>` attribute.  This is a 2d array with one item for each of the Mechanism's
`Input_states <Mechanism_InputStates>.  The result of the :keyword:`function` is placed in the Mechanism's
`value <Mechanism_Base.value>` attribute, which is also a 2d array with one or more items.  The
Mechanism's :keyword:`value` is used by its `outputStates <Mechanism_OutputStates>` to generate their :keyword:`value`
attributes, each of which is assigned as an item of the list in the Mechanism's
`output_values <Mechanism_Base.output_values>` attribute.

.. note::
   The input to a Mechanism is not necessarily the same as the input to its `function <Mechanism_Base.function>`.
   The input to a Mechanism is first Processed by its InputState(s), and then assigned to the Mechanism's
   `variable <Mechanism_Base>` attribute, which is used as the input to its `function <Mechanism_Base.function>`.
   Similarly, the result of a Mechanism's function is not necessarily the same as the Mechanism's output.  The result
   of the `function <Mechanism_Base.function>` is assigned to the Mechanism's  `value <Mechanism_Base.value>` attribute,
   which is then used by its outputStates to assign items to its `output_values <Mechanism_Base.output_values>` attribute.

.. _Mechanism_States:

States
~~~~~~

Every Mechanism has three types of States (shown schematically in the figure below):

.. _Mechanism_Figure:

.. figure:: _static/Mechanism_States_fig.svg
   :alt: Mechanism States
   :scale: 75 %
   :align: left

   **Schematic of a Mechanism showing its three types of States** (input, parameter and output). Every Mechanism has at
   least one InputState (its `primary InputState <Mechanism_InputStates>` ) and one OutputState
   (its `primary OutputState <OutputState_Primary>`), and can have additional ones of each.  It also has one
   `ParameterState` for each of its parameters and the parameters of its `function <Mechanism.function>`.

.. _Mechanism_InputStates:

InputStates
^^^^^^^^^^^

These receive and represent the input to a Mechanism. A Mechanism usually has only one (**primary**) `InputState`, 
identified by its `input_state, <Mechanism_Base.input_state>` attribute.  However some Mechanisms have
more  than one InputState. For example, a `ComparatorMechanism` has one InputState for its `sample` and another for its
`target` input. If a Mechanism has more than one InputState, they are identified in a ContentAddressableList in the 
Mechanism's `input_states <Mechanism_Base.input_states>` attribute (note the plural).  A specific InputState in the
list can be accessed by using its name as the index for the list (e.g., my_mechanism['InputState name'].

COMMENT:
[TBI:]
If the InputState are created automatically, or are not assigned a name when specified, then each is named
using the following template: [TBI]
COMMENT

Each InputState of a Mechanism can receive one or more Projections from other Mechanisms.  If the Mechanism is an
`ORIGIN` Mechanism of a Process, it also receives a `Projection` from the `ProcessInputState <Process_Input_And_Output>`
for that Process. Each InputState's :keyword:`function <InputState.InputState.function>` aggregates the values received
from its Projections (usually by summing them), and assigns the result to the InputState's :keyword:`value` attribute.

.. _Mechanism_Variable:

The value of each InputState for the Mechanism is assigned as the value of an item of the Mechanism's
`variable <Mechanism_Base.variable>` attribute (a 2d np.array), as well as in a corresponding item of its
`input_value <Mechanism_Base.input_value>` attribute (a list).  The :keyword:`variable` provides the input to the
Mechanism's `function <Mechanism_Base.function>`, while its :kewyord:`input_value` provides a more convenient way
of accessing its individual items.

COMMENT:
The number of input_states for the Mechanism must match the number of tems specified for the Mechanism's
``variable`` (that is, its size along its first dimension, axis 0).  An exception is if the Mechanism's `variable``
has more than one item, but only a single InputState;  in that case, the ``value`` of that InputState must have the
same number of items as the Mechanisms's ``variable``.
COMMENT

.. _Mechanism_ParameterStates:

ParameterStates
^^^^^^^^^^^^^^^

These represent the parameters that determine the operation of a Mechanism, including the parameters of its
:keyword:`function`.  One `ParameterState` is assigned to each of the parameters of the Mechanism
and/or its :keyword:`function` (these correspond to the arguments in their constructors).  Like other States,
ParameterStates can receive Projections. Typically these are from the `ControlProjections <ControlProjection>`
of a `ControlMechanism` that is used to modify parameter values in response to the outcome(s) of
processing.  A parameter value (and the value of its associated ParameterState) can be specified when a Mechanism or
its function is first created  using the corresponding argument in the object's constructor.  Parameter values can
also be assigned later, by direct assignment of a value to the corresponding attribute, or by using the Mechanism's 
`assign_param` method (the safest means;  see `ParameterState_Specifying_Parameters`).  All of the Mechanism's
parameters are list in a dict in its `user_params` attribute; the dict contains a `function_params` entry which
in turn contains a dict of the parameters for the Mechanism's `function <Mechanism.function>`.

.. _Mechanism_OutputStates:

OutputStates
^^^^^^^^^^^^
These represent the output(s) of a Mechanism. A Mechanism can have several `outputStates <OutputState>`, and each can
send Projections that transmit its value to other Mechanisms and/or the output of the `Process` or `System` to which
the Mechanism belongs.  Every Mechanism has at least one OutputState, referred to as its 
`primary OutputState <OutputState_Primary>`.  If outputStates are not explicitly specified for a Mechanism, a primary 
OutputState is automatically created and assigned to its `OutputState <Mechanism.Mechanism_Base.outputState>` 
attribute (note the singular), and also to the first entry of the Mechanism's `outputStates 
<Mechanism.Mechanism_Base.outputStates>` attribute (note the plural).  The `value <OutputState.value>` of the primary 
OutputState is assigned as the first (and often only) item of the Mechanism's 
`output_value <Mechanism.Mechanism_Base.output_value>`, which is the result of the Mechanism`s 
`function <Mechanism.Mechanism_Base.function>`.  Additional outputStates can be assigned to represent values derived 
from the result of the Mechanism's `function <Mechanism.function>`.  Standard outputStates are available for each 
type of Mechanism, and custom ones can also be configured (see `OutputState Specification <OutputState_Specification>`.
These can be assigned in the **output_states** argument of the Mechanism's constructor.  All of the outputStates of a 
Mechanism (including the primary one) are represented in its `output_states <Mechanism_Base.outputStates>` attribute 
(note the plural), that contains a ContentAddressableList of the outputStates.  A specific OutputState in the list can 
be accessed by using its name as the index for the list (e.g., my_mechanism['OutputState name'].  This can also be
used to assign additional outputStates to the Mechanism after it has been created.

.. _Mechanism_Parameters:

Mechanism Parameters
~~~~~~~~~~~~~~~~~~~~

COMMENT:
   ADD: SIZE XXXXX
   REFORMAT TO DESCRIBE SPECIFICATION AS ARGS IN CONSTRUCTOR RATHER THAN AS ENTRIES IN PARAMS DICT
COMMENT

Most Mechanisms implement a standard set of parameters, that can be specified by direct reference to the corresponding
attribute of the Mechanisms (e.g., myMechanism.attribute), in a 
`parameter dictionary <ParameterState_Specifying_Parameters>` assigned to `params` argument in the Mechanism's
constructor, or with the Mechanism's `assign_params` method, using the following keywords:

    * *INPUT_STATES* - specifies specialized input_states required by a Mechanism subclass
      (see :ref:`InputState specification <InputState_Creation>` for details of specification).
    ..
    * *FUNCTION* - specifies the `function <Mechanism_Base.function>` for the Mechanism;  can be one of several
      functions pre-specified by the subclass or a user-defined `custom function <Mechanism_Custom_Function>`.
    ..
    * *FUNCTION_PARAMS* - a specification dictionary of parameters for the Mechanism's :keyword:`function`;
      the key for each entry must be the name of one of the function's parameters;  its value can be any of the
      following (see :ref:`ParameterState_Specifying_Parameters` for details):

      * the value of the parameter itself;
      |
      * a `ParameterState`, the value of which specifies the parameter's value (see `ParameterState_Creation`);
      |
      * a ControlProjection or LearningProjection specification (see `Projection_Creation`),
        that assigns the parameter its default value, and a Projection to it's ParameterState of the specified type;
      |
      * a tuple with exactly two items: the parameter value and a Projection type specifying a
        `LearningProjection`, `ControlProjection` or `GatingProjection`.
      |
      .. note::
         Some Mechanism subclasses include the function parameters as arguments in Mechanism's constructor.
         Any values specified in the `FUNCTION__PARAMS` entry of a 
         `parameter specification dictionary <ParameterState_Specifying_Parameters>` for the Mechanism take precedence 
         over values assigned to parameter-specific arguments in its (or its function's) constructor.

    * *OUTPUT_STATES* - specifies specialized outputStates required by a Mechanism subclass
      (see :ref:`OutputStates_Creation` for details of specification).
    ..
    * *MONITOR_FOR_CONTROL* - specifies which of the Mechanism's outputStates is monitored by the `controller`
      for the System to which the Mechanism belongs (see :ref:`specifying monitored outputStates
      <ControlMechanism_Monitored_OutputStates>` for details of specification).
    ..
    * *MONITOR_FOR_LEARNING* - specifies which of the Mechanism's outputStates is used for learning
      (see `Learning <LearningMechanism_Activation_Output>` for details of specification).

The parameters of a Mechanism are listed in a dictionary in its `params <Mechanism_Base.params>
attribute;  the key for each entry is the name of the parameter, and its value is the parameter's value.
Each parameter is also an attribute of the Mechanism (the name of which is the name of the parameter).
The parameters of the Mechanism's function are listed in the Mechanism's `function_params` attribute.

COMMENT:
    FOR DEVELOPERS:
    + FUNCTION : function or method :  method used to transform Mechanism input to its output;
        This must be implemented by the subclass, or an exception will be raised;
        each item in the variable of this method must be compatible with a corresponding InputState;
        each item in the output of this method must be compatible  with the corresponding OutputState;
        for any parameter of the method that has been assigned a ParameterState,
        the output of the ParameterState's own execute method must be compatible with
        the value of the parameter with the same name in params[FUNCTION_PARAMS] (EMP)
    + FUNCTION_PARAMS (dict):
        NOTE: function parameters can be specified either as arguments in the Mechanism's __init__ method
        (** EXAMPLE ??), or by assignment of the function_params attribute for paramClassDefaults (** EXMAMPLE ??).
        Only one of these methods should be used, and should be chosen using the following principle:
        - if the Mechanism implements one function, then its parameters should be provided as arguments in the __init__
        - if the Mechanism implements several possible functions and they do not ALL share the SAME parameters,
            then the function should be provided as an argument but not they parameters; they should be specified
            as arguments in the specification of the function
        each parameter is instantiated as a ParameterState
        that will be placed in <Mechanism>._parameter_states;  each parameter is also referenced in
        the <Mechanism>.function_params dict, and assigned its own attribute (<Mechanism>.<param>).
COMMENT

.. _Mechanism_Role_In_Processes_And_Systems:

Role in Processes and Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mechanisms that are part of one or more processes are assigned designations that indicate the
`role <Process_Mechanisms>` they play in those processes, and similarly for `role <System_Mechanisms>` they play in
any systems to which they belong. These designations are listed in the Mechanism's `processes` and `systems`
attributes, respectively.  Any Mechanism designated as `ORIGIN` receives a Projection to its
`primary InputState <Mechanism_InputStates>` from the Process(es) to which it belongs.  Accordingly, when the Process 
(or System of which the Process is a part) is executed, those mechainsms receive the input provided to the Process 
(or System).  The `output_values <Mechanism_Base.output_values>` of any Mechanism designated as the `TERMINAL` 
Mechanism for a Process is assigned as the `output` of that Process, and similarly for systems to which it belongs.

.. note:: A Mechanism can be the `ORIGIN` or `TERMINAL` of a Process but not of a System to which that
          Process belongs;  see :ref:`Chain Example <LINK>` for further explanation.


.. _Mechanism_Execution:

Execution
---------

A Mechanism can be executed using its `execute <Mechanism_Base.execute>` or `run <Mechanism_Base.run>` methods.  This
can be useful in testing a Mechanism and/or debugging.  However, more typically, Mechanisms are executed as part of a
`Process <Process_Execution>` or `System <System_Execution>`.  For either of these, the Mechanism must be included in
the `pathway` of a Process.  There, it can be specified on its own, or as the first item of a tuple that also has an
optional set of `runtime parameters <Mechanism_Runtime_Parameters>`, and/or a `phase specification <System_Phase>` for
use when  executed in a System (see `Process_Mechanisms` for additional details about specifying a Mechanism in a
Process `pathway`).

.. _Mechanism_Runtime_Parameters:

Runtime Parameters
~~~~~~~~~~~~~~~~~~

.. note::
   This is an advanced feature, and is generally not required for most applications.

The parameters of a Mechanism are usually specified when the Mechanism is created.  However, these can be overridden
when it executed.  This can be done in a `parameter specification dictionary <ParameterState_Specifying_Parameters>` 
assigned to the **runtime_param** argument of the Mechanism's `execute <Mechanism_Base.execute>` method, or in a
`tuple with the Mechanism <Process_Mechanisms>` in the `pathway` of a `Process`.  Any value assigned to a
parameter in a **runtime_params** dictionary will override the current value of that parameter for the (and *only* the)
current execution of the Mechanism; the value will return to its previous value following current round of execution, 
unless the `runtimeParamStickyAssignmentPref` is set for the component to which the parameter belongs.

The runtime parameters for a Mechanism are specified using a dictionary that contains one or more entries, each of
which is for a parameter of the Mechanism or its  function, or for one of the Mechanism's `States <State>`.
Entries for parameters of the Mechanism or its function use the standard format for
`parameter specification dictionaries <ParameterState_Specifying_Parameters>`. Entries for the Mechanism's States can
be used to specify runtime parameters of the corresponding State, its function, or any of the Projections to that State.
Each State entry uses a key corresponding to the type of State (*INPUT_STATE_PARAMS*, *OUTPUT_STATE_PARAMS* or
*PARAMETER_STATE_PARAMS*), and the value is a subdictionary containing a dictionary with the runtime  parameter
specifications for all States of that type). Within that subdictionary, specification of parameters for the State or
its function use the  standard format for `parameter dictionaries <ParameterState_Specifying_Parameters>`.  Parameters
for all of the State's Projections can be specified in an entry with the key *PROJECTION_PARAMS*, and a subdictionary
that contains the parameter specifications;  parameters for Projections of a particular type can be placed in an
entry with a key specifying the type (*MAPPING_PROJECTION_PARAMS*, *LEARNING_PROJECTION_PARAMS*,
*CONTROL_PROJECTION_PARAMS*, or *GATING_PROJECTION_PARAMS*; and parameters can for a specific Projection can be
placed in an entry with a key specifying the name of the project and a dictionary with the specifications.

COMMENT:
    ADD EXAMPLE(S) HERE
COMMENT

COMMENT:
?? DO PROJECTION DICTIONARIES PERTAIN TO INCOMING OR OUTGOING PROJECTIONS OR BOTH??
?? CAN THE KEY FOR A STATE DICTIONARY REFERENCE A SPECIFIC STATE BY NAME, OR ONLY STATE-TYPE??

State keyword: dict for State's params
    Function or Projection keyword: dict for Funtion or Projection's params
        parameter keyword: vaue of param

    dict: can be one (or more) of the following:
        + INPUT_STATE_PARAMS:<dict>
        + PARAMETER_STATE_PARAMS:<dict>
   [TBI + OUTPUT_STATE_PARAMS:<dict>]
        - each dict will be passed to the corresponding State
        - params can be any permissible executeParamSpecs for the corresponding State
        - dicts can contain the following embedded dicts:
            + FUNCTION_PARAMS:<dict>:
                 will be passed the State's execute method,
                     overriding its paramInstanceDefaults for that call
            + PROJECTION_PARAMS:<dict>:
                 entry will be passed to all of the State's Projections, and used by
                 by their execute methods, overriding their paramInstanceDefaults for that call
            + MAPPING_PROJECTION_PARAMS:<dict>:
                 entry will be passed to all of the State's MappingProjections,
                 along with any in a PROJECTION_PARAMS dict, and override paramInstanceDefaults
            + LEARNING_PROJECTION_PARAMS:<dict>:
                 entry will be passed to all of the State's LearningProjections,
                 along with any in a PROJECTION_PARAMS dict, and override paramInstanceDefaults
            + CONTROL_PROJECTION_PARAMS:<dict>:
                 entry will be passed to all of the State's ControlProjections,
                 along with any in a PROJECTION_PARAMS dict, and override paramInstanceDefaults
            + GATING_PROJECTION_PARAMS:<dict>:
                 entry will be passed to all of the State's GatingProjections,
                 along with any in a PROJECTION_PARAMS dict, and override paramInstanceDefaults
            + <ProjectionName>:<dict>:
                 entry will be passed to the State's Projection with the key's name,
                 along with any in the PROJECTION_PARAMS and MappingProjection or ControlProjection dicts
COMMENT

.. _Mechanism_Class_Reference:

Class Reference
---------------

"""

import logging

from collections import OrderedDict
from inspect import isclass

from PsyNeuLink.Components.ShellClasses import *
from PsyNeuLink.Globals.Registry import register_category

logger = logging.getLogger(__name__)
MechanismRegistry = {}

class MonitoredOutputStatesOption(AutoNumber):
    """Specifies outputStates to be monitored by a `ControlMechanism` (see `ControlMechanism_Monitored_OutputStates
    for a more complete description of their meanings."""
    ONLY_SPECIFIED_OUTPUT_STATES = ()
    """Only monitor explicitly specified outputstates."""
    PRIMARY_OUTPUT_STATES = ()
    """Monitor only the `primary OutputState <OutputState_Primary>` of a mechanism."""
    ALL_OUTPUT_STATES = ()
    """Monitor all outputStates <Mechanism.Mechanism_Base.outputStates>` of a mechanism."""
    NUM_MONITOR_STATES_OPTIONS = ()


class MechanismError(Exception):
    def __init__(self, error_value):
        self.error_value = error_value

    def __str__(self):
        return repr(self.error_value)


def mechanism(mech_spec=None, params=None, context=None):
    """Factory method for Mechanism; returns the type of Mechanism specified or a default Mechanism.
    If called with no arguments, returns the `default Mechanism <LINK>`.

    Arguments
    ---------

    mech_spec : Optional[Mechanism subclass, str, or dict]
        specification for the Mechanism to create.
        If it is the name of a Mechanism subclass, a default instance of that subclass is returned.
        If it is string that is the name of a Mechanism subclass registered in the `MechanismRegistry`,
        an instance of a `default Mechanism <LINK>` for *that class* is returned;
        otherwise, the string is used to name an instance of the `default Mechanism <LINK>.
        If it is a dict, it must be a `Mechanism specification dictionary <`Mechanism_Creation>`.
        If it is `None` or not specified, an instance of the `default Mechanism <LINK>` is returned;
        the nth instance created will be named by using the Mechanism's :keyword:`componentType` attribute as the
        base for the name and adding an indexed suffix:  componentType-n.

    params : Optional[Dict[param keyword, param value]]
        a `parameter dictionary <ParameterState_Specifying_Parameters>` that can be used to specify the parameters for
        the Mechanism and/or its function, and/or a custom function and its parameters.  It is passed to the relevant
        subclass to instantiate the Mechanism. Its entries can be used to specify any parameters described in
        `Mechanism_Parameters` that are relevant to the Mechanism's subclass, and/or defined specifically by that
        particular `Mechanism` subclass.  Values specified for parameters in the dictionary override any assigned to
        those parameters in arguments of the constructor.

    COMMENT:
        context : str
            if it is the keyword VALIDATE, returns :keyword:`True` if specification would return a valid
            subclass object; otherwise returns :keyword:`False`.
    COMMENT

    Returns
    -------

    Instance of specified Mechanism subclass or None : Mechanism
    """

    # Called with a keyword
    if mech_spec in MechanismRegistry:
        return MechanismRegistry[mech_spec].mechanismSubclass(params=params, context=context)

    # Called with a string that is not in the Registry, so return default type with the name specified by the string
    elif isinstance(mech_spec, str):
        return Mechanism_Base.defaultMechanism(name=mech_spec, params=params, context=context)

    # Called with a Mechanism type, so return instantiation of that type
    elif isclass(mech_spec) and issubclass(mech_spec, Mechanism):
        return mech_spec(params=params, context=context)

    # Called with Mechanism specification dict (with type and params as entries within it), so:
    #    - get mech_type from kwMechanismType entry in dict
    #    - pass all other entries as params
    elif isinstance(mech_spec, dict):
        # Get Mechanism type from kwMechanismType entry of specification dict
        try:
            mech_spec = mech_spec[kwMechanismType]
        # kwMechanismType config_entry is missing (or mis-specified), so use default (and warn if in VERBOSE mode)
        except (KeyError, NameError):
            if Mechanism.classPreferences.verbosePref:
                print("{0} entry missing from mechanisms dict specification ({1}); default ({2}) will be used".
                      format(kwMechanismType, mech_spec, Mechanism_Base.defaultMechanism))
            return Mechanism_Base.defaultMechanism(name=kwProcessDefaultMechanism, context=context)
        # Instantiate Mechanism using mech_spec dict as arguments
        else:
            return mech_spec(context=context, **mech_spec)

    # Called without a specification, so return default type
    elif mech_spec is None:
        return Mechanism_Base.defaultMechanism(name=kwProcessDefaultMechanism, context=context)

    # Can't be anything else, so return empty
    else:
        return None


class Mechanism_Base(Mechanism):
    """Abstract class for Mechanism

    .. note::
       Mechanisms should NEVER be instantiated by a direct call to the base class.
       They should be instantiated using the :class:`mechanism` factory method (see it for description of parameters),
       by calling the constructor for the desired subclass, or using other methods for specifying a Mechanism in
       context (see :ref:`Mechanism_Creation`).

    COMMENT:
        Description
        -----------
            Mechanism is a Category of the Component class.
            A Mechanism is associated with a name and:
            - one or more input_states:
                two ways to get multiple input_states, if supported by Mechanism subclass being instantiated:
                    • specify 2d variable for Mechanism (i.e., without explicit InputState specifications)
                        once the variable of the Mechanism has been converted to a 2d array, an InputState is assigned
                        for each item of axis 0, and the corresponding item is assigned as the InputState's variable
                    • explicitly specify input_states in params[INPUT_STATES] (each with its own variable specification);
                        those variables will be concantenated into a 2d array to create the Mechanism's variable
                if both methods are used, they must generate the same sized variable for the mechanims
                ?? WHERE IS THIS CHECKED?  WHICH TAKES PRECEDENCE: InputState SPECIFICATION (IN _instantiate_state)??
            - an execute method:
                coordinates updating of input_states, _parameter_states (and params), execution of the function method
                implemented by the subclass, (by calling its _execute method), and updating of the outputStates
            - one or more parameters, each of which must be (or resolve to) a reference to a ParameterState
                these determine the operation of the function of the Mechanism subclass being instantiated
            - one or more outputStates:
                the variable of each receives the corresponding item in the output of the Mechanism's function
                the value of each is passed to corresponding MappingProjections for which the Mechanism is a sender
                * Notes:
                    by default, a Mechanism has only one OutputState, assigned to <Mechanism>.outputState;  however:
                    if params[OUTPUT_STATES] is a list (of names) or specification dict (of MechanismOuput State
                    specs), <Mechanism>.outputStates (note plural) is created and contains a dict of outputStates,
                    the first of which points to <Mechanism>.outputState (note singular)
                [TBI * each OutputState maintains a list of Projections for which it serves as the sender]

        Constraints
        -----------
            - the number of input_states must correspond to the length of the variable of the Mechanism's execute method
            - the value of each InputState must be compatible with the corresponding item in the
                variable of the Mechanism's execute method
            - the value of each ParameterState must be compatible with the corresponding parameter of  the Mechanism's
                 execute method
            - the number of outputStates must correspond to the length of the output of the Mechanism's execute method,
                (self.value)
            - the value of each OutputState must be compatible with the corresponding item of the self.value
                 (the output of the Mechanism's execute method)

        Class attributes
        ----------------
            + componentCategory = kwMechanismFunctionCategory
            + className = componentCategory
            + suffix = " <className>"
            + className (str): kwMechanismFunctionCategory
            + suffix (str): " <className>"
            + registry (dict): MechanismRegistry
            + classPreference (PreferenceSet): Mechanism_BasePreferenceSet, instantiated in __init__()
            + classPreferenceLevel (PreferenceLevel): PreferenceLevel.CATEGORY
            + variableClassDefault (list)
            + paramClassDefaults (dict):
                + MECHANISM_TIME_SCALE (TimeScale): TimeScale.TRIAL (timeScale at which Mechanism executes)
                + [TBI: kwMechanismExecutionSequenceTemplate (list of States):
                    specifies order in which types of States are executed;  used by self.execute]
            + paramNames (dict)
            + defaultMechanism (str): Currently DDM_MECHANISM (class reference resolved in __init__.py)

        Class methods
        -------------
            - _validate_variable(variable, context)
            - _validate_params(request_set, target_set, context)
            - update_states_and_execute(time_scale, params, context):
                updates input, param values, executes <subclass>.function, returns outputState.value
            - terminate_execute(self, context=None): terminates execution of Mechanism (for TimeScale = time_step)
            - adjust(params, context)
                modifies specified Mechanism params (by calling Function._instantiate_defaults)
                returns output
            - plot(): generates a plot of the Mechanism's function using the specified parameter values

        MechanismRegistry
        -----------------
            All Mechanisms are registered in MechanismRegistry, which maintains a dict for each subclass,
              a count for all instances of that type, and a dictionary of those instances
    COMMENT

    Attributes
    ----------

    variable : 2d np.array : default variableInstanceDefault
        value used as input to the Mechanism's `function <Mechanism_Base.function>`.  When specified in a constructor
        for the Mechanism, it is used as a template to define the format (length and type of elements) and default
        value of the function's input.

        .. _receivesProcessInput (bool): flags if Mechanism (as first in Pathway) receives Process input Projection

    input_state : InputState : default default InputState
        primary `InputState <Mechanism_InputStates>` for the Mechanism;  same as first entry of its `input_states
        <Mechanism_Base.input_states>` attribute.

    input_states : ContentAddressableList[str, InputState]
        a dictionary of the Mechanism's `input_states <Mechanism_InputStates>`.
        The key of each entry is the name of an InputState, and its value is the InputState.  There is always
        at least one entry, which identifies the Mechanism's `primary InputState <Mechanism_InputStates>`
        (i.e., the one in the its `InputState <Mechanism_Base.input_state>` attribute).

    input_value : List[List or 1d np.array] : default variableInstanceDefault
        a list of values, one for each `InputState <Mechanism_InputStates>` in the Mechanism's
        `input_states <Mechanism_Base.input_states>` attribute.  The value of each item is the same as the corresponding
        item in the Mechanism's `variable <Mechanism_Base.variable>` attribute.  The latter is a 2d np.array;
        the :keyword:`input_value attribute provides this information in a simpler list format.

    _parameter_states : ContentAddressableList[str, ParameterState]
        a dictionary of ParameterStates, one for each of the specifiable parameters of the Mechanism and its function
        (i.e., the ones for which there are arguments in their constructors).  The key of each entry in the
        dictionary is the name of the ParameterState, and its value is the ParameterState itself.  The value of the
        parameters of the Mechanism are also accessible as attributes of the Mechanism (using the name of the
        parameter); the function parameters are listed in the Mechanism's
        `function_params <Mechanism_Base.function_params>` attribute.

    COMMENT:
       MOVE function and function_params (and add user_params) to Component docstring
    COMMENT

    function : Function, function or method
        the primary function for the Mechanism, called when it is executed.  It takes the Mechanism's
        `variable <Mechanism_Base.variable>` attribute as its input, and its result is assigned to the Mechanism's
        `value <Mechanism_Base.value` attribute.

    function_params : Dict[str, value]
        a `parameter dictionary <ParameterState_Specifying_Parameters>` of the parameters for the Mechanism's primary
        function.  The key of each entry is the name of a function parameter, and its value is the parameter's value.
        Values specified for parameters in the dictionary override any assigned to those parameters in arguments of the
        constructor for the function.

    value : 2d np.array : default None
        output of the Mechanism's `function <Mechanism_Base.function>`.
        Note: this is not necessarily the same as the Mechanism's `output_values <Mechanism_Base.output_values>` attribute,
        which lists the values of its `outputStates <Mechanism_Base.outputStates>`.
        The keyword:`value` is `None` until the Mechanism has been executed at least once.

        .. _value_template : 2d np.array : default None
               set equal to the value attribute when the Mechanism is first initialized;
               maintains its value even when value is reset to None when (re-)initialized prior to execution.

    output_state : OutputState : default default OutputState
        primary `OutputState <Mechanism_OutputStates>` for the Mechanism;  same as first entry of its
        `outputStates <Mechanism_Base.outputStates>` attribute.

    output_states : ContentAddressableList[str, OutputState]
        a dictionary of the Mechanism's `outputStates <Mechanism_OutputStates>`.
        The key of each entry is the name of an OutputState, and its value is the OutputState.  There is always
        at least one entry, which identifies the Mechanism's `primary OutputState <OutputState_Primary>`.

    output_values : List[value] : default Mechanism.function(variableInstanceDefault)
        a list of values, one for each `OutputState <Mechanism_OutputStates>` in the Mechanism's
        :keyword:`outputStates` attribute.

        .. note:: The :keyword:`output_values` of a Mechanism is not necessarily the same as its
                  `value <Mechanism_Base.value>` attribute, since the OutputState's
                  `function <OutputState.OutputState.function>` and/or its `calculate <Mechanism_Base.calculate>`
                  attribute may use the Mechanism's `value <Mechanism_Base.value>` to generate a derived quantity for
                  the `value <OutputState.OutputState.value>` of the OutputState and its corresponding item in the
                  the Mechanism's :keyword:`output_values` attribute.

        COMMENT:
            EXAMPLE HERE
        COMMENT

        .. _outputStateValueMapping : Dict[str, int]:
               contains the mappings of outputStates to their indices in the output_values list
               The key of each entry is the name of an OutputState, and the value is its position in the
                    :py:data:`outputStates <Mechanism_Base.outputStates>` OrderedDict.
               Used in ``_update_output_states`` to assign the value of each OutputState to the correct item of
                   the Mechanism's ``value`` attribute.
               Any Mechanism with a function that returns a value with more than one item (i.e., len > 1) MUST implement
                   self.execute rather than just use the params[FUNCTION].  This is so that _outputStateValueMapping
                   can be implemented.
               TBI: if the function of a Mechanism is specified only by params[FUNCTION]
                   (i.e., it does not implement self.execute) and it returns a value with len > 1
                   it MUST also specify kwFunctionOutputStateValueMapping.

    is_finished : bool : default False
        set by a Mechanism to signal completion of its execution; used by `Conditions_Component_Based` to predicate
        the execution of one or more other Components on the Mechanism.

    phaseSpec : int or float :  default 0
        determines the `TIME_STEP`\ (s) at which the Mechanism is executed as part of a System
        (see :ref:`Process_Mechanisms` for specification, and :ref:`System Phase <System_Execution_Phase>`
        for how phases are used).

    processes : Dict[Process, str]:
        a dictionary of the processes to which the Mechanism belongs, and a
        `designation of its role <Mechanism_Role_In_Processes_And_Systems>` in each.  The key of each entry is a
        Process to which the Mechanism belongs, and its value the Mechanism's
        `designation in that Process <Process_Mechanisms>`.

    systems : Dict[System, str]:
        a dictionary of the systems to which the Mechanism belongs, and a
        `designation of its role <Mechanism_Role_In_Processes_And_Systems>` in each.
        The key of each entry is a System to which the Mechanism belongs, and its value the Mechanism's
        `designation in that System <System_Mechanisms>`.

    time_scale : TimeScale : default TimeScale.TRIAL
        determines the default value of the `TimeScale` used by the Mechanism when executed.

    name : str : default <Mechanism subclass>-<index>
        the name of the Mechanism.
        Specified in the **name** argument of the constructor for the Mechanism;  if not is specified,
        a default is assigned by `MechanismRegistry` based on the Mechanism's subclass
        (see `Registry <LINK>` for conventions used in naming, including for default and duplicate names).

    prefs : PreferenceSet or specification dict : Mechanism.classPreferences
        the `PreferenceSet` for the Mechanism.
        Specified in the **prefs** argument of the constructor for the Mechanism;
        if it is not specified, a default is assigned using `classPreferences` defined in __init__.py
        (see :doc:`PreferenceSet <LINK>` for details).

        .. _stateRegistry : Registry
               registry containing dicts for each State type (InputState, OutputState and ParameterState) with instance
               dicts for the instances of each type and an instance count for each State type in the Mechanism.
               Note: registering instances of State types with the Mechanism (rather than in the StateRegistry)
                     allows the same name to be used for instances of a State type belonging to different Mechanisms
                     without adding index suffixes for that name across Mechanisms
                     while still indexing multiple uses of the same base name within a Mechanism.

    """

    #region CLASS ATTRIBUTES
    componentCategory = kwMechanismComponentCategory
    className = componentCategory
    suffix = " " + className

    registry = MechanismRegistry

    classPreferenceLevel = PreferenceLevel.CATEGORY
    # Any preferences specified below will override those specified in CategoryDefaultPreferences
    # Note: only need to specify setting;  level will be assigned to CATEGORY automatically
    # classPreferences = {
    #     kwPreferenceSetName: 'MechanismCustomClassPreferences',
    #     kp<pref>: <setting>...}


    #FIX:  WHEN CALLED BY HIGHER LEVEL OBJECTS DURING INIT (e.g., PROCESS AND SYSTEM), SHOULD USE FULL Mechanism.execute
    # By default, init only the _execute method of Mechanism subclass objects when their execute method is called;
    #    that is, DO NOT run the full Mechanism execute Process, since some components may not yet be instantiated
    #    (such as outputStates)
    initMethod = INIT__EXECUTE__METHOD_ONLY

    # IMPLEMENTATION NOTE: move this to a preference
    defaultMechanism = DDM_MECHANISM


    variableClassDefault = [0.0]
    # Note:  the following enforce encoding as 2D np.ndarrays,
    #        to accomodate multiple States:  one 1D np.ndarray per state
    variableEncodingDim = 2
    valueEncodingDim = 2

    # Category specific defaults:
    paramClassDefaults = Component.paramClassDefaults.copy()
    paramClassDefaults.update({
        INPUT_STATES:None,
        OUTPUT_STATES:None,
        MONITOR_FOR_CONTROL: NotImplemented,  # This has to be here to "register" it as a valid param for the class
                                              # but is set to NotImplemented so that it is ignored if it is not
                                              # assigned;  setting it to None actively disallows assignment
                                              # (see EVCMechanism_instantiate_input_states for more details)
        MONITOR_FOR_LEARNING: None,
        # TBI - kwMechanismExecutionSequenceTemplate: [
        #     Components.States.InputState.InputState,
        #     Components.States.ParameterState.ParameterState,
        #     Components.States.OutputState.OutputState]
        MECHANISM_TIME_SCALE: TimeScale.TRIAL
        })

    # def __new__(cls, *args, **kwargs):
    # def __new__(cls, name=NotImplemented, params=NotImplemented, context=None):
    #endregion

    @tc.typecheck
    def __init__(self,
                 variable=None,
                 input_states=None,
                 output_states=None,
                 params=None,
                 name=None,
                 prefs=None,
                 context=None):
        """Assign name, category-level preferences, register Mechanism, and enforce category methods

        This is an abstract class, and can only be called from a subclass;
           it must be called by the subclass with a context value

        NOTES:
        * Since Mechanism is a subclass of Component, it calls super.__init__
            to validate variable_default and param_defaults, and assign params to paramInstanceDefaults;
            it uses INPUT_STATE as the variable_default
        * registers Mechanism with MechanismRegistry

        """

        # Forbid direct call to base class constructor
        if context is None or (not isinstance(context, type(self)) and not VALIDATE in context):
            # raise MechanismError("Direct call to abstract class Mechanism() is not allowed; "
                                 # "use mechanism() or one of the following subclasses: {0}".
                                 # format(", ".join("{!s}".format(key) for (key) in MechanismRegistry.keys())))
                                 # format(", ".join("{!s}".format(key) for (key) in MechanismRegistry.keys())))
            raise MechanismError("Direct call to abstract class Mechanism() is not allowed; "
                                 "use Mechanism() or a subclass")

        # IMPLEMENT **kwargs (PER State)


        # Ensure that all input_states and output_states, whether from paramClassDefaults or constructor arg,
        #    have been included in user_params and implemented as properties
        #    (in case the subclass did not include one and/or the other as an argument in its constructor)

        kwargs = {}

        # input_states = []
        # if INPUT_STATES in self.paramClassDefaults and self.paramClassDefaults[INPUT_STATES]:
        #     input_states.extend(self.paramClassDefaults[INPUT_STATES])
        # if INPUT_STATES in self.user_params and self.user_params[INPUT_STATES]:
        #     input_states.extend(self.user_params[INPUT_STATES])
        # if input_states:
        #     kwargs[INPUT_STATES] = input_states
        #
        # output_states = []
        # if OUTPUT_STATES in self.paramClassDefaults and self.paramClassDefaults[OUTPUT_STATES]:
        #     output_states.extend(self.paramClassDefaults[OUTPUT_STATES])
        # if OUTPUT_STATES in self.user_params and self.user_params[OUTPUT_STATES]:
        #     output_states.extend(self.user_params[OUTPUT_STATES])
        # if output_states:
        #     kwargs[OUTPUT_STATES] = output_states
        #
        # kwargs[PARAMS] = params
        #
        # params = self._assign_args_to_param_dicts(**kwargs)

        self._execution_id = None
        self.is_finished = False

        # Register with MechanismRegistry or create one
        if not context is VALIDATE:
            register_category(entry=self,
                              base_class=Mechanism_Base,
                              name=name,
                              registry=MechanismRegistry,
                              context=context)

        # Create Mechanism's _stateRegistry and state type entries
        from PsyNeuLink.Components.States.State import State_Base
        self._stateRegistry = {}

        # InputState
        from PsyNeuLink.Components.States.InputState import InputState
        register_category(entry=InputState,
                          base_class=State_Base,
                          registry=self._stateRegistry,
                          context=context)
        # ParameterState
        from PsyNeuLink.Components.States.ParameterState import ParameterState
        register_category(entry=ParameterState,
                          base_class=State_Base,
                          registry=self._stateRegistry,
                          context=context)
        # OutputState
        from PsyNeuLink.Components.States.OutputState import OutputState
        register_category(entry=OutputState,
                          base_class=State_Base,
                          registry=self._stateRegistry,
                          context=context)

        # Mark initialization in context
        if not context or isinstance(context, object) or inspect.isclass(context):
            context = INITIALIZING + self.name + SEPARATOR_BAR + self.__class__.__name__
        else:
            context = context + SEPARATOR_BAR + INITIALIZING + self.name

        super(Mechanism_Base, self).__init__(variable_default=variable,
                                             param_defaults=params,
                                             prefs=prefs,
                                             name=name,
                                             context=context)

        # FUNCTIONS:

# IMPLEMENTATION NOTE:  REPLACE THIS WITH ABC (ABSTRACT CLASS)
        # Assign class functions
        self.classMethods = {
            kwMechanismExecuteFunction: self.execute,
            # kwMechanismAdjustFunction: self.adjust_function,
            # kwMechanismTerminateFunction: self.terminate_execute
        }
        self.classMethodNames = self.classMethods.keys()

        #  Validate class methods:
        #    make sure all required ones have been implemented in (i.e., overridden by) subclass
        for name, method in self.classMethods.items():
            try:
                method
            except (AttributeError):
                raise MechanismError("{0} is not implemented in Mechanism class {1}".
                                     format(name, self.name))

        self.value = self._old_value = None
        self._status = INITIALIZING
        self._receivesProcessInput = False
        self.phaseSpec = None
        self.processes = {}
        self.systems = {}


    def _validate_variable(self, variable, context=None):
        """Convert variableClassDefault and self.variable to 2D np.array: one 1D value for each InputState

        # VARIABLE SPECIFICATION:                                        ENCODING:
        # Simple value variable:                                         0 -> [array([0])]
        # Single state array (vector) variable:                         [0, 1] -> [array([0, 1])
        # Multiple state variables, each with a single value variable:  [[0], [0]] -> [array[0], array[0]]

        :param variable:
        :param context:
        :return:
        """

        super(Mechanism_Base, self)._validate_variable(variable, context)

        # Force Mechanism variable specification to be a 2D array (to accomodate multiple InputStates - see above):
        # Note: _instantiate_input_states (below) will parse into 1D arrays, one for each InputState
        self.variableClassDefault = convert_to_np_array(self.variableClassDefault, 2)
        self.variable = convert_to_np_array(self.variable, 2)

    def _filter_params(self, params):
        """Add rather than override INPUT_STATES and/or OUTPUT_STATES

        Allows specification of INPUT_STATES or OUTPUT_STATES in params dictionary to be added to,
        rather than override those in paramClassDefaults (the default behavior)
        """

        import copy

        # INPUT_STATES:

        # Check if input_states is in params (i.e., was specified in arg of constructor)
        if not INPUT_STATES in params or params[INPUT_STATES] is None:
            # If it wasn't, assign from paramClassDefaults (even if it is None) to force creation of input_states attrib
            if self.paramClassDefaults[INPUT_STATES] is not None:
                params[INPUT_STATES] = copy.deepcopy(self.paramClassDefaults[INPUT_STATES])
            else:
                params[INPUT_STATES] = None
        # Convert input_states_spec to list if it is not one
        if params[INPUT_STATES] is not None and not isinstance(params[INPUT_STATES], (list, dict)):
            params[INPUT_STATES] = [params[INPUT_STATES]]
        self.user_params.__additem__(INPUT_STATES, params[INPUT_STATES])

        # OUTPUT_STATES:

        # Check if OUTPUT_STATES is in params (i.e., was specified in arg of contructor)
        if not OUTPUT_STATES in params or params[OUTPUT_STATES] is None:
            if self.paramClassDefaults[OUTPUT_STATES] is not None:
                params[OUTPUT_STATES] = copy.deepcopy(self.paramClassDefaults[OUTPUT_STATES])
            else:
                params[OUTPUT_STATES] = None
        # Convert OUTPUT_STATES_spec to list if it is not one
        if params[OUTPUT_STATES] is not None and not isinstance(params[OUTPUT_STATES], (list, dict)):
            params[OUTPUT_STATES] = [params[OUTPUT_STATES]]
        self.user_params.__additem__(OUTPUT_STATES, params[OUTPUT_STATES])

        # try:
        #     input_states_spec = params[INPUT_STATES]
        # except KeyError:
        #     pass
        # else:
        #     # Convert input_states_spec to list if it is not one
        #     if not isinstance(input_states_spec, list):
        #         input_states_spec = [input_states_spec]
        #     # # Get input_states specified in paramClassDefaults
        #     # if self.paramClassDefaults[INPUT_STATES] is not None:
        #     #     default_input_states = self.paramClassDefaults[INPUT_STATES].copy()
        #     # else:
        #     #     default_input_states = None
        #     # # Convert input_states from paramClassDefaults to a list if it is not one
        #     # if default_input_states is not None and not isinstance(default_input_states, list):
        #     #     default_input_states = [default_input_states]
        #     # # Add InputState specified in params to those in paramClassDefaults
        #     # #    Note: order is important here;  new ones should be last, as paramClassDefaults defines the
        #     # #          the primary InputState which must remain first for the input_states ContentAddressableList
        #     # default_input_states.extend(input_states_spec)
        #     # # Assign full set back to params_arg
        #     # params[INPUT_STATES] = default_input_states
        #
        #     # Get inputStates specified in paramClassDefaults
        #     if self.paramClassDefaults[INPUT_STATES] is not None:
        #         default_input_states = self.paramClassDefaults[INPUT_STATES].copy()
        #         # Convert inputStates from paramClassDefaults to a list if it is not one
        #         if not isinstance(default_input_states, list):
        #             default_input_states = [default_input_states]
        #         # Add input_states specified in params to those in paramClassDefaults
        #         #    Note: order is important here;  new ones should be last, as paramClassDefaults defines the
        #         #          the primary InputState which must remain first for the input_states ContentAddressableList
        #         default_input_states.extend(input_states_spec)
        #         # Assign full set back to params_arg
        #         params[INPUT_STATES] = default_input_states

        # # OUTPUT_STATES:
        # try:
        #     output_states_spec = params[OUTPUT_STATES]
        # except KeyError:
        #     pass
        # else:
        #     # Convert output_states_spec to list if it is not one
        #     if not isinstance(output_states_spec, list):
        #         output_states_spec = [output_states_spec]
        #     # Get outputStates specified in paramClassDefaults
        #     default_output_states = self.paramClassDefaults[OUTPUT_STATES].copy()
        #     # Convert outputStates from paramClassDefaults to a list if it is not one
        #     if not isinstance(default_output_states, list):
        #         default_output_states = [default_output_states]
        #     # Add output_states specified in params to those in paramClassDefaults
        #     #    Note: order is important here;  new ones should be last, as paramClassDefaults defines the
        #     #          the primary OutputState which must remain first for the output_states ContentAddressableList
        #     default_output_states.extend(output_states_spec)
        #     # Assign full set back to params_arg
        #     params[OUTPUT_STATES] = default_output_states

    def _validate_params(self, request_set, target_set=None, context=None):
        """validate TimeScale, INPUT_STATES, FUNCTION_PARAMS, OUTPUT_STATES and MONITOR_FOR_CONTROL
        
        Go through target_set params (populated by Component._validate_params) and validate values for:
            + TIME_SCALE:  <TimeScale>
            + INPUT_STATES:
                <MechanismsInputState or Projection object or class,
                specification dict for one, 2-item tuple, or numeric value(s)>;
                if it is missing or not one of the above types, it is set to self.variable
            + FUNCTION_PARAMS:  <dict>, every entry of which must be one of the following:
                ParameterState or Projection object or class, specification dict for one, 2-item tuple, or numeric 
                value(s);
                if invalid, default (from paramInstanceDefaults or paramClassDefaults) is assigned
            + OUTPUT_STATES:
                <MechanismsOutputState object or class, specification dict, or numeric value(s);
                if it is missing or not one of the above types, it is set to None here;
                    and then to default value of self.value (output of execute method) in instantiate_output_state
                    (since execute method must be instantiated before self.value is known)
                if OUTPUT_STATES is a list or OrderedDict, it is passed along (to instantiate_output_states)
                if it is a OutputState class ref, object or specification dict, it is placed in a list
            + MONITORED_STATES:
                ** DOCUMENT

        Note: PARAMETER_STATES are validated separately -- ** DOCUMENT WHY

        TBI - Generalize to go through all params, reading from each its type (from a registry),
                                   and calling on corresponding subclass to get default values (if param not found)
                                   (as PROJECTION_TYPE and PROJECTION_SENDER are currently handled)
        """

        # Perform first-pass validation in Function.__init__():
        # - returns full set of params based on subclass paramClassDefaults
        super(Mechanism, self)._validate_params(request_set,target_set,context)

        params = target_set

        #VALIDATE TIME SCALE
        try:
            param_value = params[TIME_SCALE]
        except KeyError:
            if any(context_string in context for context_string in {COMMAND_LINE, SET_ATTRIBUTE}):
                pass
            else:
                self.timeScale = timeScaleSystemDefault
        else:
            if isinstance(param_value, TimeScale):
                self.timeScale = params[TIME_SCALE]
            else:
                if self.prefs.verbosePref:
                    print("Value for {0} ({1}) param of {2} must be of type {3};  default will be used: {4}".
                          format(TIME_SCALE, param_value, self.name, type(TimeScale), timeScaleSystemDefault))

        # VALIDATE INPUT STATE(S)

        # INPUT_STATES is specified, so validate:
        if INPUT_STATES in params and params[INPUT_STATES] is not None:

            param_value = params[INPUT_STATES]

            # If it is a single item or a non-OrderedDict, place in a list (for use here and in instantiate_inputState)
            if not isinstance(param_value, (list, OrderedDict, ContentAddressableList)):
                param_value = [param_value]
            # Validate each item in the list or OrderedDict
            # Note:
            # * number of input_states is validated against length of the owner Mechanism's variable
            #     in instantiate_inputState, where an input_state is assigned to each item of variable
            i = 0
            for key, item in param_value if isinstance(param_value, dict) else enumerate(param_value):
                from PsyNeuLink.Components.States.InputState import InputState
                # If not valid...
                if not ((isclass(item) and (issubclass(item, InputState) or # InputState class ref
                                                issubclass(item, Projection))) or    # Project class ref
                            isinstance(item, InputState) or      # InputState object
                            isinstance(item, dict) or            # InputState specification dict
                            isinstance(item, str) or             # Name (to be used as key in input_states dict)
                            iscompatible(item, **{kwCompatibilityNumeric: True})):   # value
                    # set to None, so it is set to default (self.variable) in instantiate_inputState
                    param_value[key] = None
                    if self.prefs.verbosePref:
                        print("Item {0} of {1} param ({2}) in {3} is not a"
                              " InputState, specification dict or value, nor a list of dict of them; "
                              "variable ({4}) of execute method for {5} will be used"
                              " to create a default OutputState for {3}".
                              format(i,
                                     INPUT_STATES,
                                     param_value,
                                     self.__class__.__name__,
                                     self.variable,
                                     self.execute.__self__.name))
                i += 1
            params[INPUT_STATES] = param_value

        # INPUT_STATES is not specified
        else:
            # pass if call is from assign_params (i.e., not from an init method)
            if any(context_string in context for context_string in {COMMAND_LINE, SET_ATTRIBUTE}):
                pass
            else:
                # INPUT_STATES not specified:
                # - set to None, so that it is set to default (self.variable) in instantiate_inputState
                # - if in VERBOSE mode, warn in instantiate_inputState, where default value is known
                params[INPUT_STATES] = None

        # VALIDATE FUNCTION_PARAMS
        try:
            function_param_specs = params[FUNCTION_PARAMS]
        except KeyError:
            if any(context_string in context for context_string in {COMMAND_LINE, SET_ATTRIBUTE}):
                pass
            elif self.prefs.verbosePref:
                print("No params specified for {0}".format(self.__class__.__name__))
        else:
            if not (isinstance(function_param_specs, dict)):
                raise MechanismError("{0} in {1} must be a dict of param specifications".
                                     format(FUNCTION_PARAMS, self.__class__.__name__))
            # Validate params
            from PsyNeuLink.Components.States.ParameterState import ParameterState
            for param_name, param_value in function_param_specs.items():
                try:
                    default_value = self.paramInstanceDefaults[FUNCTION_PARAMS][param_name]
                except KeyError:
                    raise MechanismError("{0} not recognized as a param of execute method for {1}".
                                         format(param_name, self.__class__.__name__))
                if not ((isclass(param_value) and
                             (issubclass(param_value, ParameterState) or
                                  issubclass(param_value, Projection))) or
                        isinstance(param_value, ParameterState) or
                        isinstance(param_value, Projection) or
                        isinstance(param_value, dict) or
                        iscompatible(param_value, default_value)):
                    params[FUNCTION_PARAMS][param_name] = default_value
                    if self.prefs.verbosePref:
                        print("{0} param ({1}) for execute method {2} of {3} is not a ParameterState, "
                              "projection, tuple, or value; default value ({4}) will be used".
                              format(param_name,
                                     param_value,
                                     self.execute.__self__.componentName,
                                     self.__class__.__name__,
                                     default_value))

        # VALIDATE OUTPUT STATE(S)

        # OUTPUT_STATES is specified, so validate:
        if OUTPUT_STATES in params and params[OUTPUT_STATES] is not None:

            param_value = params[OUTPUT_STATES]

            # If it is a single item or a non-OrderedDict, place in list (for use here and in instantiate_output_state)
            if not isinstance(param_value, (ContentAddressableList, list, OrderedDict)):
                param_value = [param_value]
            # Validate each item in the list or OrderedDict
            i = 0
            for key, item in param_value if isinstance(param_value, dict) else enumerate(param_value):
                from PsyNeuLink.Components.States.OutputState import OutputState
                # If not valid...
                if not ((isclass(item) and issubclass(item, OutputState)) or # OutputState class ref
                            isinstance(item, OutputState) or   # OutputState object
                            isinstance(item, dict) or                   # OutputState specification dict
                            isinstance(item, str) or                    # Name (to be used as key in outputStates dict)
                            iscompatible(item, **{kwCompatibilityNumeric: True})):  # value
                    # set to None, so it is set to default (self.value) in instantiate_output_state
                    param_value[key] = None
                    if self.prefs.verbosePref:
                        print("Item {0} of {1} param ({2}) in {3} is not a"
                              " OutputState, specification dict or value, nor a list of dict of them; "
                              "output ({4}) of execute method for {5} will be used"
                              " to create a default OutputState for {3}".
                              format(i,
                                     OUTPUT_STATES,
                                     param_value,
                                     self.__class__.__name__,
                                     self.value,
                                     self.execute.__self__.name))
                i += 1
            params[OUTPUT_STATES] = param_value

        # OUTPUT_STATES is not specified
        else:
            # pass if call is from assign_params (i.e., not from an init method)
            if any(context_string in context for context_string in {COMMAND_LINE, SET_ATTRIBUTE}):
                pass
            else:
                # OUTPUT_STATES not specified:
                # - set to None, so that it is set to default (self.value) in instantiate_output_state
                # Notes:
                # * if in VERBOSE mode, warning will be issued in instantiate_output_state, where default value is known
                # * number of outputStates is validated against length of owner Mechanism's execute method output (EMO)
                #     in instantiate_output_state, where an OutputState is assigned to each item (value) of the EMO
                params[OUTPUT_STATES] = None

    def _validate_inputs(self, inputs=None):
        # Only ProcessingMechanism supports run() method of Function;  ControlMechanism and LearningMechanism do not
        raise MechanismError("{} does not support run() method".format(self.__class__.__name__))

    def _instantiate_attributes_before_function(self, context=None):

        self._instantiate_input_states(context=context)
        self._instantiate_parameter_states(context=context)
        super()._instantiate_attributes_before_function(context=context)

    def _instantiate_function(self, context=None):
        """Assign weights and exponents if specified in input_states
        """

        super()._instantiate_function(context=context)

        if self.input_states and any(input_state.weight is not None for input_state in self.input_states):

            # Construct defaults:
            #    from function_object.weights if specified else 1's
            try:
                default_weights = self.function_object.weights
            except AttributeError:
                default_weights = None
            if default_weights is None:
                default_weights = default_weights or [1.0] * len(self.input_states)

            # Assign any weights specified in input_state spec
            weights = [[input_state.weight if input_state.weight is not None else default_weight]
                       for input_state, default_weight in zip(self.input_states, default_weights)]
            self.function_object._weights = weights

        if self.input_states and any(input_state.exponent is not None for input_state in self.input_states):

            # Construct defaults:
            #    from function_object.weights if specified else 1's
            try:
                default_exponents = self.function_object.exponents
            except AttributeError:
                default_exponents = None
            if default_exponents is None:
                default_exponents = default_exponents or [1.0] * len(self.input_states)

            # Assign any exponents specified in input_state spec
            exponents = [[input_state.exponent if input_state.exponent is not None else default_exponent]
                       for input_state, default_exponent in zip(self.input_states, default_exponents)]
            self.function_object._exponents = exponents

    def _instantiate_attributes_after_function(self, context=None):

        self._instantiate_output_states(context=context)
        super()._instantiate_attributes_after_function(context=context)

    def _instantiate_input_states(self, context=None):
        """Call State._instantiate_input_states to instantiate orderedDict of InputState(s)

        This is a stub, implemented to allow Mechanism subclasses to override _instantiate_input_states
        """
        from PsyNeuLink.Components.States.InputState import _instantiate_input_states
        _instantiate_input_states(owner=self, context=context)

    def _instantiate_parameter_states(self, context=None):
        """Call State._instantiate_parameter_states to instantiate a ParameterState for each parameter in user_params

        This is a stub, implemented to allow Mechanism subclasses to override _instantiate_parameter_states
        """

        from PsyNeuLink.Components.States.ParameterState import _instantiate_parameter_states
        _instantiate_parameter_states(owner=self, context=context)

    def _instantiate_output_states(self, context=None):
        """Call State._instantiate_output_states to instantiate orderedDict of OutputState(s)

        This is a stub, implemented to allow Mechanism subclasses to override _instantiate_output_states
        """
        from PsyNeuLink.Components.States.OutputState import _instantiate_output_states
        _instantiate_output_states(owner=self, context=context)

    def _add_projection_to_mechanism(self, state, projection, context=None):

        from PsyNeuLink.Components.Projections.Projection import _add_projection_to
        _add_projection_to(receiver=self, state=state, projection_spec=projection, context=context)

    def _add_projection_from_mechanism(self, receiver, state, projection, context=None):
        """Add projection to specified state
        """
        from PsyNeuLink.Components.Projections.Projection import _add_projection_from
        _add_projection_from(sender=self, state=state, projection_spec=projection, receiver=receiver, context=context)

    def execute(self,
                input=None,
                runtime_params=None,
                clock=CentralClock,
                time_scale=TimeScale.TRIAL,
                ignore_execution_id = False,
                context=None):
        """Carry out a single execution of the Mechanism.


        COMMENT:
            Update InputState(s) and parameter(s), call subclass _execute, update OutputState(s), and assign self.value

            Execution sequence:
            - Call self.input_state.execute() for each entry in self.input_states:
                + execute every self.input_state.path_afferents.[<Projection>.execute()...]
                + aggregate results and/or gate state using self.input_state.function()
                + assign the result in self.input_state.value
            - Call every self.params[<ParameterState>].execute(); for each:
                + execute self.params[<ParameterState>].mod_afferents.[<Projection>.execute()...]
                    (usually this is just a single ControlProjection)
                + aggregate results for each ModulationParam or assign value from an OVERRIDE specification
                + assign the result to self.params[<ParameterState>].value
            - Call subclass' self.execute(params):
                - use self.input_state.value as its variable,
                - use self.params[<ParameterState>].value for each param of subclass' self.function
                - call self._update_output_states() to assign the output to each self.output_states[<OutputState>].value
                Note:
                * if execution is occurring as part of initialization, each output_state is reset to 0
                * otherwise, their values are left as is until the next update
        COMMENT

        Arguments
        ---------

        input : List[value] or ndarray : default variableInstanceDefault
            input to use for execution of the Mechanism.
            This must be consistent with the format of the Mechanism's InputState(s):
            the number of items in the  outermost level of the list, or axis 0 of the ndarray, must equal the number
            of the Mechanism's `input_states  <Mechanism_Base.input_states>`, and each item must be compatible with the
            format (number and type of elements) of the corresponding InputState's
            `variable <InputState.InputState.variable>` (see `Run Inputs <Run_Inputs>` for details of input
            specification formats).

        runtime_params : Optional[Dict[str, Dict[str, Dict[str, value]]]]:
            a dictionary that can include any of the parameters used as arguments to instantiate the Mechanism,
            its function, or Projection(s) to any of its States.  Any value assigned to a parameter will override
            the current value of that parameter for the (and only the current) execution of the Mechanism, and will
            return to its previous value following execution (unless the `runtimeParamStickyAssignmentPref` is set
            for the component to which the parameter belongs).  See `runtime_params <Mechanism_Runtime_Parameters>` 
            above for details concerning specification.
              
        time_scale : TimeScale :  default TimeScale.TRIAL
            specifies whether the Mechanism is executed for a single time_step or a trial.

        Returns
        -------

        Mechanism's output_values : List[value]
            list of the :keyword:`value` of each of the Mechanism's `outputStates <Mechanism_OutputStates>` after
            either one time_step or a trial.

        """
        self.ignore_execution_id = ignore_execution_id
        context = context or NO_CONTEXT

        # IMPLEMENTATION NOTE: Re-write by calling execute methods according to their order in functionDict:
        #         for func in self.functionDict:
        #             self.functionsDict[func]()

        # Limit init to scope specified by context
        if INITIALIZING in context:
            if PROCESS_INIT in context or SYSTEM_INIT in context:
                # Run full execute method for init of Process and System
                pass
            # Only call subclass' _execute method and then return (do not complete the rest of this method)
            elif self.initMethod is INIT__EXECUTE__METHOD_ONLY:
                return_value =  self._execute(variable=self.variable,
                                                 runtime_params=runtime_params,
                                                 clock=clock,
                                                 time_scale=time_scale,
                                                 context=context)

                # # # MODIFIED 3/3/17 OLD:
                # # return np.atleast_2d(return_value)
                # # MODIFIED 3/3/17 NEW:
                # converted_to_2d = np.atleast_2d(return_value)
                # MODIFIED 3/7/17 NEWER:
                # IMPLEMENTATION NOTE:  THIS IS HERE BECAUSE IF return_value IS A LIST, AND THE LENGTH OF ALL OF ITS
                #                       ELEMENTS ALONG ALL DIMENSIONS ARE EQUAL (E.G., A 2X2 MATRIX PAIRED WITH AN
                #                       ARRAY OF LENGTH 2), np.array (AS WELL AS np.atleast_2d) GENERATES A ValueError
                if (isinstance(return_value, list) and
                    (all(isinstance(item, np.ndarray) for item in return_value) and
                        all(
                                all(item.shape[i]==return_value[0].shape[0]
                                    for i in range(len(item.shape)))
                                for item in return_value))):

                        return return_value
                else:
                    converted_to_2d = np.atleast_2d(return_value)
                # If return_value is a list of heterogenous elements, return as is
                #     (satisfies requirement that return_value be an array of possibly multidimensional values)
                if converted_to_2d.dtype == object:
                    return return_value
                # Otherwise, return value converted to 2d np.array
                else:
                    return converted_to_2d
                # MODIFIED 3/3/17 END

            # Call only subclass' function during initialization (not its full _execute method nor rest of this method)
            elif self.initMethod is INIT_FUNCTION_METHOD_ONLY:
                return_value = self.function(variable=self.variable,
                                             params=runtime_params,
                                             time_scale=time_scale,
                                             context=context)
                return np.atleast_2d(return_value)


        #region VALIDATE RUNTIME PARAMETER SETS
        # Insure that param set is for a States:
        if self.prefs.paramValidationPref:
            if runtime_params:
                # runtime_params can have entries for any of the the Mechanism's params, or
                #    one or more state keys, each of which should be for a params dictionary for the corresponding
                #    state type, and each of can contain only parameters relevant to that state
                state_keys = [INPUT_STATE_PARAMS, PARAMETER_STATE_PARAMS, OUTPUT_STATE_PARAMS]
                param_names = list({**self.user_params, **self.function_params})
                if not all(key in state_keys + param_names for key in runtime_params):
                        raise MechanismError("There is an invalid specification for a runtime parameter of {}".
                                             format(self.name))
                # for state_key in runtime_params:
                for state_key in [entry for entry in runtime_params if entry in state_keys]:
                    state_dict = runtime_params[state_key]
                    if not isinstance(state_dict, dict):
                        raise MechanismError("runtime_params entry for {} is not a dict".
                                             format(self.name, state_key))
                    for param_name in state_dict:
                        if not param_name in param_names:
                            raise MechanismError("{} entry in runtime_params for {} "
                                                 "contains an unrecognized parameter: {}".
                                                 format(state_key, self.name, param_name))

        #endregion

        # FIX: ??MAKE CONDITIONAL ON self.prefs.paramValidationPref??
        #region VALIDATE INPUT STATE(S) AND RUNTIME PARAMS
        self._check_args(variable=self.variable,
                        params=runtime_params,
                        target_set=runtime_params)
        #endregion

        #region UPDATE INPUT STATE(S)

        # Executing or simulating Process or System, get input by updating input_states

        if input is None and (EXECUTING in context or EVC_SIMULATION in context) and (self.input_state.path_afferents != []):
            self._update_input_states(runtime_params=runtime_params, time_scale=time_scale, context=context)

        # Direct call to execute Mechanism with specified input, so assign input to Mechanism's input_states
        else:
            if context is NO_CONTEXT:
                context = EXECUTING + ' ' + append_type_to_name(self)
            if input is None:
                input = self.variableClassDefault
            self._assign_input(input)

        #endregion

        #region UPDATE PARAMETER STATE(S)
        self._update_parameter_states(runtime_params=runtime_params, time_scale=time_scale, context=context)
        #endregion

        #region CALL SUBCLASS _execute method AND ASSIGN RESULT TO self.value

        self.value = self._execute(variable=self.variable,
                                      runtime_params=runtime_params,
                                      clock=clock,
                                      time_scale=time_scale,
                                      context=context)

        # # MODIFIED 3/3/17 OLD:
        # self.value = np.atleast_2d(self.value)
        # # MODIFIED 3/3/17 NEW:
        # converted_to_2d = np.atleast_2d(self.value)
        # # If self.value is a list of heterogenous elements, leave as is;
        # # Otherwise, use converted value (which is a genuine 2d array)
        # if converted_to_2d.dtype != object:
        #     self.value = converted_to_2d
        # MODIFIED 3/8/17 NEWER:
        # IMPLEMENTATION NOTE:  THIS IS HERE BECAUSE IF return_value IS A LIST, AND THE LENGTH OF ALL OF ITS
        #                       ELEMENTS ALONG ALL DIMENSIONS ARE EQUAL (E.G., A 2X2 MATRIX PAIRED WITH AN
        #                       ARRAY OF LENGTH 2), np.array (AS WELL AS np.atleast_2d) GENERATES A ValueError
        if (isinstance(self.value, list) and
            (all(isinstance(item, np.ndarray) for item in self.value) and
                all(
                        all(item.shape[i]==self.value[0].shape[0]
                            for i in range(len(item.shape)))
                        for item in self.value))):
                # return self.value
                pass
        else:
            converted_to_2d = np.atleast_2d(self.value)
            # If return_value is a list of heterogenous elements, return as is
            #     (satisfies requirement that return_value be an array of possibly multidimensional values)
            if converted_to_2d.dtype == object:
                # return self.value
                pass
            # Otherwise, return value converted to 2d np.array
            else:
                # return converted_to_2d
                self.value = converted_to_2d
        # MODIFIED 3/3/17 END

        # Set status based on whether self.value has changed
        self.status = self.value

        #endregion


        #region UPDATE OUTPUT STATE(S)
        self._update_output_states(runtime_params=runtime_params, time_scale=time_scale, context=context)
        #endregion

        #region REPORT EXECUTION
        if self.prefs.reportOutputPref and context and EXECUTING in context:
            self._report_mechanism_execution(self.input_values, self.user_params, self.output_state.value)
        #endregion

        #region RE-SET STATE_VALUES AFTER INITIALIZATION
        # If this is (the end of) an initialization run, restore state values to initial condition
        if '_init_' in context:
            for state in self.input_states:
                self.input_states[state].value = self.input_states[state].variable
            for state in self._parameter_states:
                self._parameter_states[state].value =  getattr(self, '_'+state)
            for state in self.output_states:
                # Zero outputStates in case of recurrence:
                #    don't want any non-zero values as a residuum of initialization runs to be
                #    transmittted back via recurrent Projections as initial inputs
                self.output_states[state].value = self.output_states[state].value * 0.0
        #endregion

        #endregion

        return self.value

    def run(self,
            inputs,
            num_executions=None,
            call_before_execution=None,
            call_after_execution=None,
            time_scale=None):
        """Run a sequence of executions.

        COMMENT:
            Call execute method for each in a sequence of executions specified by the `inputs` argument.
        COMMENT

        Arguments
        ---------

        inputs : List[input] or ndarray(input) : default default_input_value
            the inputs used for each in a sequence of executions of the Mechanism (see `Run_Inputs` for a detailed
            description of formatting requirements and options).

        call_before_execution : function : default None
            called before each execution of the Mechanism.

        call_after_execution : function : default None
            called after each execution of the Mechanism.

        time_scale : TimeScale : default TimeScale.TRIAL
            specifies whether the Mechanism is executed for a single time_step or a trial.

        Returns
        -------

        Mechanism's output_values : List[value]
            list of the :keyword:`value` of each of the Mechanism's `outputStates <Mechanism_OutputStates>` for
            each execution of the Mechanism.

        """
        from PsyNeuLink.Globals.Run import run
        return run(self,
                   inputs=inputs,
                   num_executions=num_executions,
                   call_before_trial=call_before_execution,
                   call_after_trial=call_after_execution,
                   time_scale=time_scale)

    def _assign_input(self, input):

        input = np.atleast_2d(input)
        num_inputs = np.size(input,0)
        num_input_states = len(self.input_states)
        if num_inputs != num_input_states:
            # Check if inputs are of different lengths (indicated by dtype == np.dtype('O'))
            num_inputs = np.size(input)
            if isinstance(input, np.ndarray) and input.dtype is np.dtype('O') and num_inputs == num_input_states:
                pass
            else:
                raise SystemError("Number of inputs ({0}) to {1} does not match "
                                  "its number of input_states ({2})".
                                  format(num_inputs, self.name,  num_input_states ))
        for i in range(num_input_states):
            # input_state = list(self.input_states.values())[i]
            input_state = self.input_states[i]
            # input_item = np.ndarray(input[i])
            input_item = input[i]

            if len(input_state.variable) == len(input_item):
                input_state.value = input_item
            else:
                raise MechanismError("Length ({}) of input ({}) does not match "
                                     "required length ({}) for input to {} of {}".
                                     format(len(input_item),
                                            input[i],
                                            len(input_state.variable),
                                            input_state.name,
                                            append_type_to_name(self)))
        self.variable = np.array(self.input_values)

    def _update_input_states(self, runtime_params=None, time_scale=None, context=None):
        """ Update value for each InputState in self.input_states:

        Call execute method for all (MappingProjection) Projections in InputState.path_afferents
        Aggregate results (using InputState execute method)
        Update InputState.value
        """
        for i in range(len(self.input_states)):
            state = self.input_states[i]
            state.update(params=runtime_params, time_scale=time_scale, context=context)
            # self.input_value[i] = state.value
        self.variable = np.array(self.input_values)

    def _update_parameter_states(self, runtime_params=None, time_scale=None, context=None):

        for state in self._parameter_states:

            # state_name = state.name

            state.update(params=runtime_params, time_scale=time_scale, context=context)

    def _update_output_states(self, runtime_params=None, time_scale=None, context=None):
        """Execute function for each OutputState and assign result of each to corresponding item of self.output_values

        """
        for state in self.output_states:
            state.update(params=runtime_params, time_scale=time_scale, context=context)

    def initialize(self, value):
        """Assign an initial value to the Mechanism's `value <Mechanism_Base.value>` attribute and update its
        `outputStates <Mechanism_Base.outputStates>`.

        COMMENT:
            Takes a number or 1d array and assigns it to the first item of the Mechanism's
            `value <Mechanism_Base.value>` attribute.
        COMMENT

        Arguments
        ----------
        value : List[value] or 1d ndarray
            value used to initialize the first item of the Mechanism's `value <Mechanism_Base.value>` attribute.

        """
        if self.paramValidationPref:
            if not iscompatible(value, self.value):
                raise MechanismError("Initialization value ({}) is not compatiable with value of {}".
                                     format(value, append_type_to_name(self)))
        self.value[0] = value
        self._update_output_states()

    def _execute(self,
                    variable=None,
                    runtime_params=None,
                    clock=CentralClock,
                    time_scale=None,
                    context=None):
        return self.function(variable=variable, params=runtime_params, time_scale=time_scale, context=context)

    def _report_mechanism_execution(self, input_val=None, params=None, output=None):

        if input_val is None:
            input_val = self.input_values
        if output is None:
            output = self.output_state.value
        params = params or self.user_params

        import re
        if 'mechanism' in self.name or 'Mechanism' in self.name:
            mechanism_string = ' '
        else:
            mechanism_string = ' mechanism'

        # kmantel: previous version would fail on anything but iterables of things that can be cast to floats
        #   if you want more specific output, you can add conditional tests here
        try:
            input_string = [float("{:0.3}".format(float(i))) for i in input_val].__str__().strip("[]")
        except TypeError:
            input_string = input_val

        print ("\n\'{}\'{} executed:\n- input:  {}".
               format(self.name,
                      mechanism_string,
                      input_string))

        if params:
            print("- params:")
            # Sort for consistency of output
            params_keys_sorted = sorted(params.keys())
            for param_name in params_keys_sorted:
                # No need to report:
                #    function_params here, as they will be reported for the function itself below;
                #    input_states or output_states, as these are not really params
                if param_name in {FUNCTION_PARAMS, INPUT_STATES, OUTPUT_STATES}:
                    continue
                param_is_function = False
                param_value = params[param_name]
                if isinstance(param_value, Function):
                    param = param_value.name
                    param_is_function = True
                elif isinstance(param_value, type(Function)):
                    param = param_value.__name__
                    param_is_function = True
                elif isinstance(param_value, (function_type, method_type)):
                    param = param_value.__self__.__class__.__name__
                    param_is_function = True
                else:
                    param = param_value
                print ("\t{}: {}".format(param_name, str(param).__str__().strip("[]")))
                if param_is_function:
                    # Sort for consistency of output
                    func_params_keys_sorted = sorted(self.function_object.user_params.keys())
                    for fct_param_name in func_params_keys_sorted:
                        print ("\t\t{}: {}".
                               format(fct_param_name,
                                      str(self.function_object.user_params[fct_param_name]).__str__().strip("[]")))

        # kmantel: previous version would fail on anything but iterables of things that can be cast to floats
        #   if you want more specific output, you can add conditional tests here
        try:
            output_string = re.sub(r'[\[,\],\n]', '', str([float("{:0.3}".format(float(i))) for i in output]))
        except TypeError:
            output_string = output

        print("- output: {}".format(output_string))


    def plot(self,x_range = None):
        """
        Generate a plot of the mechanism's function using the specified parameter values. See (see
        `DDM.plot <DDM.plot>` for details of the animated DDM plot).

        Arguments
        ---------

        x_range: List
             specify the range over which the function should be plotted. x_range must be provides as a list containing
             two floats: lowest value of x and highest value of x.  Default values depend on the mechanism's function.

            - Logistic Function: default x_range = [-5.0, 5.0]
            - Exponential Function: default x_range = [0.1, 5.0]
            - All Other Functions: default x_range = [-10.0, 10.0]



        Returns
        -------
        Mechanism's function plot : Matplotlib window
            Matplotlib window of the Mechanism's function plotted with specified parameters over the specified x_range

        """

        import matplotlib.pyplot as plt

        if not x_range:
            if "Logistic" in str(self.function):
                x_range= [-5.0, 5.0]
            elif "Exponential" in str(self.function):
                x_range = [0.1, 5.0]
            else:
                x_range = [-10.0, 10.0]
        x_space = np.linspace(x_range[0],x_range[1])
        plt.plot(x_space, self.function(x_space), lw=3.0, c='r')
        plt.show()

    def _get_mechanism_param_values(self):
        """Return dict with current value of each ParameterState in paramsCurrent
        :return: (dict)
        """
        from PsyNeuLink.Components.States.ParameterState import ParameterState
        return dict((param, value.value) for param, value in self.paramsCurrent.items()
                    if isinstance(value, ParameterState) )

    def _get_primary_state(self, state_type):
        from PsyNeuLink.Components.States.InputState import InputState
        from PsyNeuLink.Components.States.ParameterState import ParameterState
        from PsyNeuLink.Components.States.OutputState import OutputState
        if issubclass(state_type, InputState):
            return self.input_state
        if issubclass(state_type, OutputState):
            return self.output_state
        if issubclass(state_type, ParameterState):
            raise Mechanism("PROGRAM ERROR:  illegal call to {} for a primary {}".format(self.name, PARAMETER_STATE))


    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, assignment):
        self._value = assignment

        # # MODIFIED 1/28/17 NEW: [COPIED FROM State]
        # # Store value in log if specified
        # # Get logPref
        # if self.prefs:
        #     log_pref = self.prefs.logPref
        #
        # # Get context
        # try:
        #     curr_frame = inspect.currentframe()
        #     prev_frame = inspect.getouterframes(curr_frame, 2)
        #     context = inspect.getargvalues(prev_frame[1][0]).locals['context']
        # except KeyError:
        #     context = ""
        #
        # # If context is consistent with log_pref, record value to log
        # if (log_pref is LogLevel.ALL_ASSIGNMENTS or
        #         (log_pref is LogLevel.EXECUTION and EXECUTING in context) or
        #         (log_pref is LogLevel.VALUE_ASSIGNMENT and (EXECUTING in context and kwAssign in context))):
        #     self.log.entries[self.name] = LogEntry(CurrentTime(), context, assignment)
        # # MODIFIED 1/28/17 END

    @property
    def input_state(self):
        return self.input_states[0]

    @property
    def input_values(self):
        try:
            return self.input_states.values
        except (TypeError, AttributeError):
            return None

    @property
    def output_state(self):
        return self.output_states[0]

    @property
    def output_values(self):
        return self.output_states.values

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, current_value):
        # if current_value != self._old_value:
        try:
            if np.array_equal(current_value, self._old_value):
                self._status = UNCHANGED
            else:
                self._status = CHANGED
                self._old_value = current_value
        # FIX:  CATCHES ELEMENTWISE COMPARISON DEPRECATION WARNING/ERROR -- NEEDS TO BE FIXED AT SOME POINT
        except:
            self._status = CHANGED


def _is_mechanism_spec(spec):
    """Evaluate whether spec is a valid Mechanism specification

    Return true if spec is any of the following:
    + Mechanism class
    + Mechanism object:
    Otherwise, return :keyword:`False`

    Returns: (bool)
    """
    if inspect.isclass(spec) and issubclass(spec, Mechanism):
        return True
    if isinstance(spec, Mechanism):
        return True
    return False

# MechanismTuple indices
# OBJECT_ITEM = 0
# # PARAMS_ITEM = 1
# # PHASE_ITEM = 2
#
# MechanismTuple = namedtuple('MechanismTuple', 'mechanism')

from collections import UserList, Iterable
class MechanismList(UserList):
    """Provides access to items and their attributes in a list of :class:`MechanismTuples` for an owner.

    :class:`MechanismTuples` are of the form: (Mechanism object, runtime_params dict, phaseSpec int).

    Attributes
    ----------
    mechanisms : list of Mechanism objects

    names : list of strings
        each item is a Mechanism.name

    values : list of values
        each item is a Mechanism.value

    outputStateNames : list of strings
        each item is an OutputState.name

    outputStateValues : list of values
        each item is an OutputState.value
    """

    def __init__(self, owner, components_list:list):
        super().__init__()
        self.mechs = components_list
        self.owner = owner
        # for item in components_list:
        #     if not isinstance(item, MechanismTuple):
        #         raise MechanismError("The following item in the components_list arg of MechanismList()"
        #                              " is not a MechanismTuple: {}".format(item))

        self.process_tuples = components_list

    def __getitem__(self, item):
        """Return specified Mechanism in MechanismList
        """
        # return list(self.mechs[item])[MECHANISM]
        return self.mechs[item]

    def __setitem__(self, key, value):
        raise ("MechanismList is read only ")

    def __len__(self):
        return (len(self.mechs))

    # def _get_tuple_for_mech(self, mech):
    #     """Return first Mechanism tuple containing specified Mechanism from the list of mechs
    #     """
    #     if list(item for item in self.mechs).count(mech):
    #         if self.owner.verbosePref:
    #             print("PROGRAM ERROR:  {} found in more than one object_item in {} in {}".
    #                   format(append_type_to_name(mech), self.__class__.__name__, self.owner.name))
    #     return next((object_item for object_item in self.mechs if object_item is mech), None)

    @property
    def mechs_sorted(self):
        """Return list of mechs sorted by Mechanism name"""
        return sorted(self.mechs, key=lambda object_item: object_item.name)

    @property
    def mechanisms(self):
        """Return list of all mechanisms in MechanismList"""
        return list(self)

    @property
    def names(self):
        """Return names of all mechanisms in MechanismList"""
        return list(item.name for item in self.mechanisms)

    @property
    def values(self):
        """Return values of all mechanisms in MechanismList"""
        return list(item.value for item in self.mechanisms)

    @property
    def outputStateNames(self):
        """Return names of all outputStates for all mechanisms in MechanismList"""
        names = []
        for item in self.mechanisms:
            for output_state in item.output_states:
                names.append(output_state.name)
        return names

    @property
    def outputStateValues(self):
        """Return values of outputStates for all mechanisms in MechanismList"""
        values = []
        for item in self.mechanisms:
            for output_state in item.output_states:
                values.append(output_state.value)
        return values
