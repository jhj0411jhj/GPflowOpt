# Copyright 2017 Joachim van der Herten
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .acquisition import Acquisition

from gpflow.models import GPModel

import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp

from gpflow.config import default_jitter, default_float


class ExpectedImprovement(Acquisition):
    """
    Expected Improvement acquisition function for single-objective global optimization.
    Introduced by (Mockus et al, 1975).

    Key reference:

    ::

       @article{Jones:1998,
            title={Efficient global optimization of expensive black-box functions},
            author={Jones, Donald R and Schonlau, Matthias and Welch, William J},
            journal={Journal of Global optimization},
            volume={13},
            number={4},
            pages={455--492},
            year={1998},
            publisher={Springer}
       }

    This acquisition function is the expectation of the improvement over the current best observation
    w.r.t. the predictive distribution. The definition is closely related to the :class:`.ProbabilityOfImprovement`,
    but adds a multiplication with the improvement w.r.t the current best observation to the integral.

    .. math::
       \\alpha(\\mathbf x_{\\star}) = \\int \\max(f_{\\min} - f_{\\star}, 0) \\, p( f_{\\star}\\,|\\, \\mathbf x, \\mathbf y, \\mathbf x_{\\star} ) \\, d f_{\\star}
    """

    def __init__(self, model):
        """
        :param model: GPflow model (single output) representing our belief of the objective
        """
        super(ExpectedImprovement, self).__init__(model)
        self.fmin = tf.Variable([1.,], dtype=default_float())
        self._setup()

    def _setup(self, feasible_data_index=None):
        super(ExpectedImprovement, self)._setup()
        # Obtain the lowest posterior mean for the previous - feasible - evaluations
        feasible_samples = self.data[0] if feasible_data_index is None else self.data[0][feasible_data_index]
        samples_mean, _ = self.models[0].predict_f(feasible_samples)
        self.fmin.assign(tf.reduce_min(samples_mean, axis=0))

    def build_acquisition(self, Xcand):
        # Obtain predictive distributions for candidates
        candidate_mean, candidate_var = self.models[0].predict_f(Xcand)
        candidate_var = tf.maximum(candidate_var, default_jitter())

        # Compute EI
        normal = tfp.distributions.Normal(candidate_mean, tf.sqrt(candidate_var))
        t1 = (self.fmin - candidate_mean) * normal.cdf(self.fmin)
        t2 = candidate_var * normal.prob(self.fmin)
        return tf.add(t1, t2, name=self.__class__.__name__)
