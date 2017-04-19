#!/bin/env python
# -*- coding: utf-8 -*-
#
#Created on 10.04.17
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
import numpy as np

# Internal modules
from .grid import Grid


logger = logging.getLogger(__name__)


class LonLatGrid(Grid):
    """
    A LonLatGrid is a grid with evenly distributed longitude and latitude values.
    This is the right grid if the grid could be described with a evenly
    distributed range of values for longitude and latitude.
    """
    def __init__(self, grid_dict):
        super().__init__(grid_dict)
        self._grid_dict = {
            'gridtype': 'lonlat',
            'xlongname': 'longitude',
            'xname': 'lon',
            'xunits': 'degrees',
            'ylongname': 'latitude',
            'yname': 'lat',
            'yunits': 'degrees',
        }
        self._grid_dict.update(grid_dict)

    def _calc_single_dim(self, dim_name='x'):
        start = self._grid_dict['{0:s}first'.format(dim_name)]
        steps = self._grid_dict['{0:s}size'.format(dim_name)]
        width = self._grid_dict['{0:s}inc'.format(dim_name)]
        calculated_dim = np.arange(
            start,
            start + steps * width,
            width)
        return calculated_dim

    def _construct_dim(self):
        return self._calc_single_dim('y'), self._calc_single_dim('x')

    def _calc_lat_lon(self):
        dim_lat, dim_lon = self._construct_dim()
        dim_lat = self.convert_to_deg(dim_lat, self._grid_dict['yunits'])
        dim_lon = self.convert_to_deg(dim_lon, self._grid_dict['xunits'])
        lat, lon = np.meshgrid(dim_lat, dim_lon)
        return lat.transpose(), lon.transpose()
