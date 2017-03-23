#!/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 16.11.16

Created for pymepps

@author: Tobias Sebastian Finn, tobias.sebastian.finn@studium.uni-hamburg.de

    Copyright (C) {2016}  {Tobias Sebastian Finn}

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
# System modules
import abc

# External modules
import xarray as xr
import pandas as pd
import pygrib

# Internal modules
from ..data_structures import File


class FileHandler(object):
    def __init__(self, file_path):
        """
        Base class for files with meteorological content. A FileHandler could
        extract the variables and metadata out of the files and could compress
        this data into one structure.

        Parameters
        ----------
        file_path : str
            The path to the file, which should be opened.
        """
        self.ds = None
        self.file = file_path
        self._var_names = None
    #
    # @property
    # def ds(self):
    #     return self._ds
    #
    # @ds.setter
    # def ds(self, ds):
    #     self._ds = ds
    @property
    def var_names(self):
        if self._var_names is None:
            self._var_names = self._get_varnames()
        return self._var_names

    @abc.abstractmethod
    def get_messages(self, var_name):
        pass

    @abc.abstractmethod
    def get_timeseries(self, var_name):
        pass

    @abc.abstractmethod
    def _get_varnames(self):
        pass

    @abc.abstractmethod
    def load_file(self):
        pass

    def get_data(self):
        pass

    def _get_metadata(self):
        pass
