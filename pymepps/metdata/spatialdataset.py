#!/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 10.12.16

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
import datetime as dt
import operator
import os.path

# External modules
import numpy as np
import xarray as xr
import cdo

# Internal modules
from .metdataset import MetDataset
from .spatialdata import SpatialData


CDO = cdo.Cdo()
logger = logging.getLogger(__name__)


class SpatialDataset(MetDataset):
    def __init__(self, file_handlers, data_origin=None):
        """
        SpatialDataset is a class for a pool of file handlers. Typically a
        spatial dataset combines the files of one model run, such that it is
        possible to select a variable and get a SpatialData instance. For
        memory reasons the data of a variable is only loaded if it is selected.

        Parameters
        ----------
        file_handlers : list of childs of FileHandler
            The spatial dataset is based on these files. The files should be
            either instances of GribHandler or NetCDFHandler.
        data_origin : optional
            The data origin. This parameter is important to trace the data
            flow. If this is None, there is no data origin and this
            dataset will be the starting point of the data flow. Default is
            None.

        Methods
        -------
        select
            Method to select a variable.
        """
        super().__init__(file_handlers, data_origin)

    def _get_file_data(self, file, var_name):
        return file.get_messages(var_name)

    def _cdo_path_helper(self, file_handler, new_path=None, inplace=False):
        in_file = file_handler.file.path
        if inplace:
            out_file = in_file
        else:
            file_name = file_handler.file.get_basename()
            if file_handler.file.get_dir == new_path:
                file_name = '{0:s}_{1:s}'.format(file_name, 'sliced')
            if new_path is not None:
                out_file = os.path.join(new_path, file_name)
            else:
                out_file = os.path.join(file_handler.file.get_dir(), file_name)
        logger.debug(
            'Set output path to {0:s} for file {1:s}'.format(out_file, in_file))
        return in_file, out_file

    def selnearest(self, lonlat, new_path=None, inplace=False):
        """
        Method to select a longitude/latitude get nearest grid point within
        every FileHandler. This method is based on the cdo command remapnn.
        For more informations see [1].
        Parameters
        ----------
        lonlat : Tuple of floats
            The lonlat, which should be extracted. This lonlat has two
            entries (lon, lat).
        inplace : bool, optional
            If True the files would be overridden. If False a '_sliced' will be
            appened to the file name. Default is True.

        Returns
        -------

        [1] https://code.zmaw.de/boards/2/topics/301
        """
        new_file_handlers = []
        for file_handler in self.file_handlers:
            in_file, out_file = self._cdo_path_helper(file_handler=file_handler,
                                                      new_path=new_path,
                                                      inplace=inplace)
            if not os.path.isfile(out_file) and in_file!=out_file:
                CDO.remapnn(
                    'lon={0:.4f}_lat={1:.4f}'.format(lonlat[0], lonlat[1]),
                    input=in_file,
                    output=out_file)
                logger.debug('Finished CDO remapnn, set new file_handler')
            else:
                logger.debug('File already exists. It\'s assumed, that this is '
                             'the already sliced file.')
            new_file_handlers.append(type(file_handler)(out_file))
        logger.debug('Finished selnearest, set new file_handlers.')
        self.file_handlers = new_file_handlers
        return self


    def sellonlatbox(self, lonlatbox, new_path=None, inplace=False):
        """
        Method to select a longitude/latitude box and slice the FileHandlers.
        This method is based on the cdo command sellonlatbox.
        Parameters
        ----------
        lonlatbox : Tuple of floats
            The lonlatbox, which should be sliced. This lonlatbox has four
            entries (left, top, right, bottom).
        inplace : bool, optional
            If True the files would be overridden. If False a '_sliced' will be
            appened to the file name. Default is True.

        Returns
        -------

        """
        new_file_handlers = []
        for file_handler in self.file_handlers:
            in_file, out_file = self._cdo_path_helper(file_handler=file_handler,
                                                      new_path=new_path,
                                                      inplace=inplace)
            if not os.path.isfile(out_file) and in_file!=out_file:
                CDO.sellonlatbox(lonlatbox[0],lonlatbox[2],lonlatbox[3],
                                 lonlatbox[1],
                                 input=in_file,
                                 output=out_file)
                logger.debug('Finished CDO sellonlatbox, set new file_handler')
            else:
                logger.debug('File already exists. It\'s assumed, that this is '
                             'the already sliced file.')
            new_file_handlers.append(type(file_handler)(out_file))
        logger.debug('Finished sellonlatbox, set new file_handlers.')
        self.file_handlers = new_file_handlers
        return self

    def data_merge(self, data):
        """
        Method to merge instances of xarray.DataArray into a SpatialData
        instance. The merge method of xarray is used.

        Parameters
        ----------
        data : list of xarray.DataArray
            The data list.

        Returns
        -------
        SpatialData
        """
        if len(data) == 1:
            logger.debug('Found only one message')
            return SpatialData(data[0], self)
        else:
            coordinate_names = list(data[0].dims)
            uniques = []
            for dim in coordinate_names[:-2]:
                dim_gen = [d[dim].values for d in data]
                uniques.append(list(np.unique(dim_gen)))
            logger.debug('Got unique coordinates')
            indexes = []
            logger.debug('Start coordinates indexing')
            for d in data:
                d_ind = [d.values]
                for key, dim in enumerate(coordinate_names[:-2]):
                    if dim in d.coords:
                        d_ind.append(uniques[key].index(d[dim].values))
                    else:
                        d_ind.append(0)
                logger.debug('Finished coordinates indexing for {0:s}'.format(str(d_ind[1:])))
                indexes.append(d_ind)
            logger.debug('Start data sorting')
            n_dims = len(coordinate_names[:-2])
            sort_dims = tuple(range(1, n_dims+1))
            sorted_data = zip(*sorted(indexes, key=operator.itemgetter(*sort_dims)))
            logger.debug('Start data reordering')
            sorted_data = np.array(list(sorted_data)[0])
            logger.debug('Start data reshaping')
            logger.debug(sorted_data.shape)
            logger.debug([len(u) for u in uniques])
            shaped_data = sorted_data.reshape(
                [len(u) for u in uniques]+
                [sorted_data.shape[-2]]+
                [sorted_data.shape[-1]])
            logger.debug('Start coordinates setting')
            coords = list(zip(coordinate_names,
                              uniques+[data[0][coordinate_names[-2]].values]+[data[0][coordinate_names[-1]].values]))
            logger.debug('Start merging')
            extracted_data = xr.DataArray(
                data=shaped_data,
                coords=coords)
            logger.debug('Start attribute setting')
            extracted_data.attrs = data[0].attrs
            logger.debug('Finished data merging')
        return SpatialData(extracted_data, self)
