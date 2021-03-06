#!/bin/env python
# -*- coding: utf-8 -*-
#
#Created on 24.05.17
#
#Created for pymepps
#
#@author: Tobias Sebastian Finn, tobias.sebastian.finn@studium.uni-hamburg.de
#
#    Copyright (C) {2017}  {Tobias Sebastian Finn}
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# System modules
import logging

# External modules

# Internal modules
from .error import ErrorMetric


logger = logging.getLogger(__name__)


class MeanSquaredError(ErrorMetric):
    """
    The MeanSquaredError class calculates the mean squared error based on 
    given data.
    """
    def _calc_metric(self, X=None, y=None):
        error_array = self._calc_error()
        mse = (error_array ** 2).mean(dim=self.iterate_axis)
        return mse


def mean_squared_error(prediction, truth, iterate_axis='runtime'):
    metric = MeanSquaredError(iterate_axis)
    return metric(prediction, truth)
