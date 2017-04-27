#!/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 09.12.16

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
import logging

# External modules
import xarray as xr

# Internal modules
from .metdata import MetData
import pymepps.plot


logger = logging.getLogger(__name__)


class SpatialData(MetData):
    def __init__(self, data_base, grid=None, data_origin=None):
        """
        SpatialData contains spatial based data structures. This class is the
        standard data type for file types like netCDF or grib. It's prepared
        for the output of numerical and statistical weather models.
        Array based data is always saved to netcdf via xarray.

        Attributes
        ----------
        data_base : xarray.DataArray or None
            The data of this grid based data structure.
        grid : Child instance of Grid or None
            The corresponding grid of this SpatialData instance. This grid is 
            used to interpolate/remap the data and to select the nearest grid
            point to a given longitude/latitude pair. The grid is also used to 
            get a basemap instance to determine the grid boundaries for plotting
            purpose.
        data_origin : object of pymepps or None, optional
            The origin of this data. This could be a model run, a station, a
            database or something else. Default is None.
        """
        super().__init__(data_base, data_origin)
        self._grid = None
        self.grid = grid

    @property
    def grid(self):
        if self._grid is None:
            raise ValueError('This spatial data has no grid defined!')
        else:
            return self._grid

    @grid.setter
    def grid(self, grid):
        if grid is not None and not hasattr(grid, '_grid_dict'):
            raise TypeError('The given grid is not a valid defined grid type!')
        self._grid = grid

    def remapnn(self, new_grid):
        pass
        #new_data = self.grid.remapnn(self.data.valu)

    def plot(self, method='contourf'):
        plot = pymepps.plot.SpatialPlot()
        plot.add_subplot()
        getattr(plot, method)(self.data)
        plot.suptitle('{0:s} plot of {1:s}'.format(method, self.data.variable))
        return plot

    def load(self, path):
        pass

    def save(self, path):
        pass