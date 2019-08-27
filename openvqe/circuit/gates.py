from openvqe import OpenVQEParameters, OpenVQEModule
from openvqe.openvqe_abc import parametrized
from dataclasses import dataclass
#from openvqe.circuit.compiler import compile_controlled_rotation_gate
import numpy as np
import copy

class WeightedGates:
	'''
	temporary idea -- a small rapper to store gates which have weights that cannot be expressed as phase, because they are not on the unit circle.
	This class exists to help with the gradients of PowerGates whose gradients aren't executable as gates due to their scaling.
	Similarly, the decomposition of pauli rotations into I and Pauli  gates produces a linear combination of gates,
	without any gaurantee that the coefficients multiplying said gates should be of modulus 1 (and hence expressable as phase).
	This class may be interepreted further by a to-be-built WeightedCircuit class, or by the get_gradient_circuits method each circuit will have
	'''
	def __init__(self,weights,gates):
		self.weights = weights
		self.gate = gates


class QGate:

    @staticmethod
    def list_assignement(o):
        """
        Helper function to make initialization with lists and single elements possible
        :param o: iterable object or single element
        :return: Gives back a list if a single element was given
        """
        if o is None:
            return None
        elif hasattr(o, "__get_item__"):
            return o
        elif hasattr(o, "__iter__"):
            return o
        else:
            return [o]

    def __init__(self, name, target: list, control: list = None, phase=1.0):
        self.name = name
        self.phase= phase
        self.target = self.list_assignement(target)
        self.control = self.list_assignement(control)
        self.verify()

    def is_frozen(self):
        raise Exception('unparametrized gates cannot be frozen because there is nothing to freeze. \n If you want to iterate over all your gates, use is_differentiable as a criterion before or in addition to is_frozen')

    def dagger(self):
        """
        :return: return the hermitian conjugate of the gate.
        """

        return QGate(name=copy.copy(self.name), target=copy.deepcopy(self.target),
                         control=copy.deepcopy(self.control),phase=np.conj(self.phase))

    def is_controlled(self) -> bool:
        """
        :return: True if the gate is controlled
        """
        return self.control is not None

    def is_parametrized(self) -> bool:
        """
        :return: True if the gate is parametrized
        """
        return False

    def is_single_qubit_gate(self) -> bool:
        """
        Convenience and easier to interpret
        :return: True if the Gate only acts on one qubit (not controlled)
        """
        return (self.control is None or len(self.control) == 0) and len(self.target) == 1

    def is_differentiable(self) -> bool:
    	'''
		defaults to False, overwridden by ParametrizedGate
    	'''
    	return False

    def verify(self):
        if self.target is None:
            raise Exception('Recieved no targets upon initialization')
        if len(self.list_assignement(self.target)) < 1:
            raise Exception('Recieved no targets upon initialization')
        if self.is_controlled():
            for c in self.target:
                if c in self.control:
                    raise Exception("control and target are the same qubit: " + self.__str__())
        if not np.isclose(np.abs(self.phase),1.0):
            raise Exception('Phase must lie on the complex unit circle (I.E, have modulus of 1)')
    def __str__(self):
        result = str(self.name) + "(target=" + str(self.target)
        if not self.is_single_qubit_gate():
            result += ", control=" + str(self.control)
        result += ")"
        return result

    def __repr__(self):
        """
        Todo: Add Nice stringification
        """
        return self.__str__()

    def max_qubit(self):
        """
        :return: highest number qubit in this gate
        """
        result = max(self.target)
        if self.control is not None:
            result = max(result, max(self.control))
        return result + 1

    def decomp(self):
        '''
        returns a restructured version of the gate, such that all supported backends have some implementation thereof.
        This may decompose poly-controlled gates into a cascade of CNOT and basis shifters, or may convert swap to a chain of cnot.
        All pre-defined gates overwrite this method to return something other than an error.
        '''
        raise NotImplementedError()

    def gradient(self):
        raise NotImplementedError()

    def is_phased(self):
        '''
        TODO: make sure this is functional.
        '''
        return self.phase not in [1.0,1.0 + 0.j]

class ParametrizedGate(QGate):
    '''
    the base class from which all parametrized gates inherit. User defined gates, when implemented, are liable to be members of this class directly.
    Has su
    '''
    def __init__(self, name, parameter, target: list, control: list = None, frozen : bool = False,phase=1.0):
        super().__init__(name,target,control,phase=phase)
        self.parameter =parameter
        if self.parameter is None:
            raise Exception('Parametrized gates require a parameter!')
        self.frozen = frozen


    def is_frozen(self):
        '''
        :return: return wether this gate is frozen or not.
        '''
        return self.frozen

    def dagger(self):
        """
        :return: return the hermitian conjugate of the gate (without decomposing)
        """
        has_angle=False
        has_power=False
        try:
            temp=self.angle
            has_angle=True
        except:
            try:
                temp=self.power
                has_power=True
            except:
                pass

        new_gate=copy.deepcopy(self)
        if has_angle == True:
            new_gate.angle=-1.0*self.parameter
        if has_power == True:
            new_gate.power =-1.0*self.parameter

        new_gate.parameter=-1.0*self.parameter
        new_gate.phase=np.conj(self.phase)
        return new_gate


    def is_parametrized(self) -> bool:
        """
        :return: True if the gate is parametrized
        """
        return True


    def is_differentiable(self) -> bool:
        """
        :return: True if the gate is differentiable
        """
        return True


    def __str__(self):
        result = str(self.name) + "(target=" + str(self.target)
        if not self.is_single_qubit_gate():
            result += ", control=" + str(self.control)

        result += ", parameter=" + str(self.parameter)
        result += ")"
        return result


    def max_qubit(self):
        """
        :return: Determine maximum qubit index needed
        """
        result = max(self.target)
        if self.control is not None:
            result = max(result, max(self.control))
        return result + 1



class RotationGate(ParametrizedGate):

    def __init__(self, name, angle, target: list, control: list = None, frozen : bool = False,phase =1.0):
        super().__init__(name,angle,target,control,frozen,phase)
        self.angle = angle
        if self.angle is None:
            raise Exception('Parametrized gates require a parameter!')


    def _rz_shorthand(self,new_angles=None):

 		#TODO: implement after the Rz, Rx, Ry CLASSES are implemented.
        '''
        helper function for recursion of recompile_gate.
        '''
        assert self.control not in [None,[]]
        assert len(new_angles) == 2
        temp=[]
        temp.append(Rz(target=self.target,angle=new_angles[0]))
        temp.append(CNOT(target=self.target,control=self.control))
        temp.append(Rz(target=self.target,angle=new_angles[1]))
        temp.append(CNOT(target=self.target,control=self.control))
        for gate in temp:
                    gate.phase=self.phase
        return temp


    def __str__(self):
        result = str(self.name) + "(target=" + str(self.target)
        if not self.is_single_qubit_gate():
            result += ", control=" + str(self.control)

        result += ", angle=" + str(self.parameter)
        result += ", phase=" +str(self.phase)
        result += ")"
        return result


class PowerGate(ParametrizedGate):

    def __init(self,name,power,target: list, control: list = None, frozen: bool = False,phase = 1.0):
        super().__init__(name,power,target,control,frozen,phase)
        self.power = power
        self.parameter = self.power
        if self.power is None:
            raise Exception('Power gates require a power!')

    def __str__(self):
        result = str(self.name) + "(target=" + str(self.target)
        if not self.is_single_qubit_gate():
            result += ", control=" + str(self.control)

        result += ", power=" + str(self.parameter)
        result += ")"
        return result

    def gradient(self):

        neo=copy.deepcopy(self)
        neo.power=self.power-1.0
        neo.parameter=neo.power
        return [{'weight':self.power,'gates':[neo]}]

######### INDIVIDUAL GATE CLASSES

class Rz(RotationGate):
    def __init__(self, angle, target: list, control: list = None, frozen : bool = False,phase=1.0):
        super().__init__('Rz',angle,target,control,frozen,phase)

    def decomp(self):
    	if self.is_controlled() is False:
    		return [self]
    	else:
    		return self._rz_shorthand(new_angles=[-self.angle/2,self.angle/2])
    def gradient(self):

        weighted_gates=[]
        if self.is_controlled() is True:
            for i,angle_set in enumerate([ [ (-self.angle +np.pi/2)/2,self.angle/2],
                [ (-self.angle -np.pi/2)/2,self.angle/2],
                [ -self.angle/2,(self.angle +np.pi/2)/2],
                [ -self.angle/2,(self.angle -np.pi/2)/2]]):
                parity= 1.0 - 2.0*(i//2) 
                new_gates=[]
                new_gates.extend(self._rz_shorthand(new_angles=angle_set))
                for gate in new_gates:
                    gate.phase=self.phase
                weighted_gates.append({'weight':0.5*parity,'gates':new_gates})

        if self.is_controlled() is False:
            neo_a=copy.deepcopy(self)
            neo_a.angle=self.angle+np.pi/2
            neo_b=copy.deepcopy(self)
            neo_b.angle=self.angle-np.pi/2
            weighted_gates.append({'weight':0.5,'gates':[neo_a]})
            weighted_gates.append({'weight':-0.5,'gates':[neo_b]})

        return weighted_gates

class Ry(RotationGate):
    def __init__(self, angle, target: list, control: list = None, frozen : bool = False,phase=1.0):
        super().__init__('Ry',angle,target,control,frozen,phase)


    def decomp(self):
        if self.is_controlled() is False:
            return [self]
        else:
            new_gates=[]
            new_gates.append(Rx(angle=np.pi/2,control=None,target=self.target,frozen=True))
            new_gates.extend(self._rz_shorthand(new_angles=[-self.angle/2,self.angle/2]))
            new_gates.append(Rx(angle=-np.pi/2,control=None,target=self.target,frozen=True))
            for gate in new_gates:
                    gate.phase=self.phase           
            return new_gates

    def gradient(self):
        weighted_gates=[]
        if self.is_controlled() is True:
            for i,angle_set in enumerate([ [ (-self.angle +np.pi/2)/2,self.angle/2],
                [ (-self.angle -np.pi/2)/2,self.angle/2],
                [ -self.angle/2,(self.angle +np.pi/2)/2],
                [ -self.angle/2,(self.angle -np.pi/2)/2]]):
                parity= 1.0 - 2.0*(i//2) 
                new_gates=[]
                new_gates.append(Rx(angle=np.pi/2,control=None,target=self.target,frozen=True))
                new_gates.extend(self._rz_shorthand(new_angles=angle_set))
                new_gates.append(Rx(angle=-np.pi/2,control=None,target=self.target,frozen=True))
                for gate in new_gates:
                    gate.phase=self.phase
                weighted_gates.append({'weight':0.5*parity,'gates':new_gates})

        if self.is_controlled() is False:
            neo_a=copy.deepcopy(self)
            neo_a.angle=self.angle+np.pi/2
            neo_b=copy.deepcopy(self)
            neo_b.angle=self.angle-np.pi/2
            weighted_gates.append({'weight':0.5,'gates':[neo_a]})
            weighted_gates.append({'weight':-0.5,'gates':[neo_b]})

        return weighted_gates

class Rx(RotationGate):
    def __init__(self, angle, target: list, control: list = None, frozen : bool = False,phase=1.0):
        super().__init__('Ry',angle,target,control,frozen,phase)
        self.angle = angle
        self.parameter = self.angle
        if self.angle is None:
            raise Exception('Rotation gates require an angle!')

    def decomp(self,grad=False):
        if self.is_controlled() is False:
            return [self]
        else:
            new_gates=[]
            new_gates.append(H(control=None,target=self.target))
            new_gates.extend(self._rz_shorthand(new_angles=[-self.angle/2,self.angle/2]))
            new_gates.append(H(control=None,target=self.target))
            for gate in new_gates:
                    gate.phase=self.phase
            return new_gates


    def gradient(self):
        weighted_gates=[]
        if self.is_controlled() is True:
            for i,angle_set in enumerate([ [ (-self.angle +np.pi/2)/2,self.angle/2],
                [ (-self.angle -np.pi/2)/2,self.angle/2],
                [ -self.angle/2,(self.angle +np.pi/2)/2],
                [ -self.angle/2,(self.angle -np.pi/2)/2]]):
                parity= 1.0 - 2.0*(i//2) 
                new_gates=[]
                new_gates.append(H(control=None,target=self.target))
                new_gates.extend(self._rz_shorthand(new_angles=angle_set))
                new_gates.append(H(control=None,target=self.target))
                for gate in new_gates:
                    gate.phase=self.phase
                weighted_gates.append({'weight':0.5*parity,'gates':new_gates})

        if self.is_controlled() is False:
            neo_a=copy.deepcopy(self)
            neo_a.angle=self.angle+np.pi/2
            neo_b=copy.deepcopy(self)
            neo_b.angle=self.angle-np.pi/2
            weighted_gates.append({'weight':0.5,'gates':[neo_a]})
            weighted_gates.append({'weight':-0.5,'gates':[neo_b]})

        return weighted_gates


class H(PowerGate):
    def __init__(self, target: list, power=1.0, control: list = None, frozen : bool = True,phase=1.0):
        super().__init__('H', power,target,control,frozen,phase)
        if self.parameter is None:
            raise Exception('Parametrized gates require a parameter!')

    def decomp(self):
        return self

class X(PowerGate):
    def __init__(self, target: list, power=1.0,control: list = None, frozen : bool = True,phase=1.0):
        super().__init__('X',power,target,control,frozen,phase)
        if self.parameter is None:
            raise Exception('Parametrized gates require a parameter!')

    def decomp(self):
        return self


class Y(PowerGate):
    def __init__(self, target: list, power=1.0, control: list = None, frozen : bool = True,phase=1.0):
        super().__init__('Y',power,target,control,frozen,phase)


    def decomp(self):
        return self

class Z(PowerGate):
    def __init__(self,  target: list, power= 1.0,control: list = None, frozen : bool = True,phase=1.0):
        super().__init__('Z',power,target,control,frozen,phase)


    def decomp(self):
        return self

class CNOT(QGate):
    def __init__(self,target,control : list,phase=1.0):
        '''
        currently we do not intend to let people use exponentiation of CNOT, hence it is not a power gate. if one seeks exponentiated cnot, 
        one should use a controlled X gate.
        '''
        super().__init__('CNOT',target,control,phase=phase)

    def dagger(self):
        return self



class SWAP(QGate):
    def __init__(self,target,control : list):
        super().__init__('SWAP',target,control,phase=1.0)
        if len(target) != 2:
            raise Exception('SWAP works on exactly two gates.')

    def dagger(self):
        return SWAP(target=self.target,control=self.control,phase=np.conj(self.phase))

    def decomp(self):
        '''
        TODO: how does the phase transfer over? phase has complicated behavior in the case of controlled gates.
        '''
        new_gates=[]
        new.gates.append(Cnot(target=target[0],control=[target[1]] +self.control))
        new.gates.append(Cnot(target=target[1],control=[target[0]] +self.control))
        new.gates.append(Cnot(target=target[0],control=[target[1]] +self.control))
        return new_gates

class I(QGate):
    def __init__(self,target:list,control: list=None,phase=1.0):
        super().__init__('I',target,control,phase)

    def decomp(self):
        '''
        if I cannot be a controlled gate on the simulator, can we just delete the control entirely, or is that not permitted, due to phase?
        '''
        return I(target=self.target,control=None,phase=self.phase)

class MS(RotationGate):
    def __init__(self, angle, target: list, control: list = None, frozen : bool = False, phase = 1.0):
        super().__init__('MS',angle,target,control,frozen,phase)
        assert len(self.target)//2 == 0 
    def decomp(self):
        #todo: implement an MS decomp in terms of X or Rx gates and cnots)
        raise Exception('sorry, no molmer-sorensen decomp yet')
    def gradient(self):
        #todo: implement
        raise Exception('sorry, no molmer-sorensen gradient yet')


