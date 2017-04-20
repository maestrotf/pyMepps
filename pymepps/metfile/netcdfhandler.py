#!/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 14.12.16

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
import re
import itertools
import collections

# External modules
import xarray as xr
import netCDF4
import numpy as np

# Internal modules
from .filehandler import FileHandler


logger = logging.getLogger(__name__)


class NetCDFHandler(FileHandler):
    def _get_varnames(self):
        self.open()
        var_names = list(self.ds.data_vars)
        self.close()
        return var_names

    def is_type(self):
        try:
            self.open()
            self.close()
            return True
        except OSError:
            return False

    def open(self):
        self.ds = xr.open_dataset(self.file)
        return self

    def close(self):
        self.ds.close()

    @property
    def lon_lat(self):
        attrs = {}
        try:
            attrs['latitude'] = float(self.ds.lat.values)
        except TypeError or KeyError:
            pass
        try:
            attrs['longitude'] = float(self.ds.lon.values)
        except TypeError or KeyError:
            pass
        try:
            attrs['altitude'] = float(self.ds.zsl.values)
        except TypeError or KeyError:
            pass
        return attrs

    def load_cube(self, var_name):
        """
        Method to load a variable from the netcdf file and return it as
        xr.DataArray.

        Parameters
        ----------
        var_name : str
            The variable name, which should be extracted.

        Returns
        -------
        variable : xr.DataArray
            The DataArray of the variable.
        """
        logger.debug('Get {0:s} from {1:s}'.format(var_name, self.file))
        variable = self.ds[var_name]
        if hasattr(variable, '_FillValue'):
            variable.values[variable.values == variable._FillValue] = np.nan
        elif hasattr(variable, 'missing_value'):
            variable.values[variable.values==variable.missing_value] = np.nan
        else:
            variable.values[variable.values==9.96921e+36] = np.nan
        return variable

    def get_timeseries(self, var_name):
        """
        Method to get the time series from a NetCDF file. This is designed for
        measurement site data in netcdf format. At the moment this method is
        only tested for Wettermast Hamburg data!

        Parameters
        ----------
        var_name : str
            The variable name, which should be extracted.

        Returns
        -------
        data : dict with pandas series
            The selected variable is extracted as dict with pandas series as
            values.
        """
        cube = self.load_cube(var_name)
        cleaned_dims = list(cube.dims)
        cleaned_dims.remove('time')
        splitted_cube = {var_name: cube,}
        for dim in cleaned_dims:
            new_cube = {}
            for temp_cube in splitted_cube:
                new_cube.update({l[0]:l[1] for l in list(
                    splitted_cube[temp_cube].groupby(dim))})
            try:
                splitted_cube = {"{0:s}_{1:s}".format(k_0, k_1):
                                     new_cube[k_0][k_1]
                                 for k_0 in new_cube for k_1 in new_cube[k_0]}
            except Exception as e:
                logger.info('Couldn\'t flatten the dict, due to {0:s}'.
                            format(e))
                splitted_cube = new_cube
        data = {k: splitted_cube[k].to_series() for k in splitted_cube}
        return data

    def _check_list_in_list(self, sublist, check_list):
        in_list = False
        for ele in check_list:
            if [sub for sub in sublist if sub in ele]:
                in_list = True
        return in_list

    def get_messages(self, var_name):
        """
        Method to imitate the message-like behaviour of grib files.

        Parameters
        ----------
        var_name : str
            The variable name, which should be extracted.

        Returns
        -------
        data : list of xr.DataArray
            The list with the message-wise data as DataArray. The DataArray
            have six coordinates (analysis, ensemble, time, level, y, x).
            The shape of DataArray are normally (1,1,1,1,y_size,x_size).
        """
        cube = self.load_cube(var_name)
        logger.debug('Loaded the cube')
        cube.attrs.update(self.ds.attrs)
        logger.debug('Updated the attributes')
        additional_coords = collections.OrderedDict()
        if not self._check_list_in_list(
                ['ana', 'runtime'], list(cube.dims[:-2])):
            try:
                ana = self._get_dates_from_path(self.file)[0]
            except IndexError:
                ana = None
            additional_coords['RunTime'] = ana
            logger.debug(
                'No analysis date within the cube found set the analysis date '
                'to {0}'.format(ana))
        if not self._check_list_in_list(
                ['ens', 'mem'], list(cube.dims[:-2])):
            ens = self._get_dates_from_path(self.file)
            additional_coords['Ensemble'] = ens
            logger.debug(
                'No ensemble member within the cube found set the ensemble '
                'to {0}'.format(ens))
        if not self._check_list_in_list(
                ['time',], list(cube.dims[:-2])):
            try:
                if 'RunTime' in additional_coords:
                    time = self._get_dates_from_path(self.file)[1]
                else:
                    time = self._get_dates_from_path(self.file)[0]
            except IndexError:
                time = None
            additional_coords['Time'] = time
            logger.debug(
                'No time within the cube found set the time to '
                '{0}'.format(time))
        ds_coords = xr.Dataset(coords=additional_coords)
        cube.coords.update(ds_coords)
        cube.expand_dims(list(additional_coords.keys()))
        logger.debug('The cube coordinates are {0}'.format(cube.coords))
        splitted_cube = [cube,]
        for dim in list(cube.dims[:-2]):
            if len(dim)>1:
                temp_cube = []
                for c in splitted_cube:
                    grouped = list(c.groupby(dim, squeeze=False))
                    set_grouped = []
                    for g in grouped:
                        if g[1][dim] == np.array([0]):
                            g[1][dim] = [g[0]]
                        set_grouped.append(g[1])
                    temp_cube.extend(set_grouped)
                splitted_cube = temp_cube
                logger.debug('Splitted {0:s}, due to length of {1:d}'.
                             format(dim, len(cube[dim])))
                logger.debug('Splitted cube dim values: {0}'.format(
                    [c[dim] for c in splitted_cube]))
        return splitted_cube
