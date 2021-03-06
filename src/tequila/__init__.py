from tequila.utils import BitString, BitNumbering, BitStringLSB, initialize_bitstring, TequilaException, TequilaWarning
from tequila.circuit import gates, QCircuit, NoiseModel
from tequila.hamiltonian import paulis, QubitHamiltonian, PauliString
from tequila.objective import Objective, VectorObjective,\
    ExpectationValue, Variable, assign_variable, format_variable_dictionary,\
    vectorize

from tequila.ml import to_platform,HAS_TORCH

from tequila.optimizers import INSTALLED_OPTIMIZERS, show_available_optimizers
from tequila.optimizers import minimize, minimize_scipy, minimize_gd, optimizer_scipy

from tequila.simulators.simulator_api import simulate, compile, compile_to_function, draw, pick_backend, \
    INSTALLED_SAMPLERS, \
    INSTALLED_SIMULATORS, SUPPORTED_BACKENDS, INSTALLED_BACKENDS, show_available_simulators
from tequila.wavefunction import QubitWaveFunction
import tequila.quantumchemistry as chemistry # shortcut

# make sure to use the jax/autograd numpy for objectives
from tequila.circuit.gradient import grad
from tequila.autograd_imports import numpy, jax, __AUTOGRAD__BACKEND__

# get rid of the jax GPU/CPU warnings
import warnings

warnings.filterwarnings("ignore", module="jax")
warnings.filterwarnings("default", category=TequilaWarning)
