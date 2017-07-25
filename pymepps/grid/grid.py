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
import abc
from copy import deepcopy

# External modules
import numpy as np
import xarray as xr
from mpl_toolkits.basemap import interp
from scipy.interpolate import griddata

# Internal modules
import pymepps


logger = logging.getLogger(__name__)


known_units = {
    'deg': lambda x: x,
    'rad': lambda x: x*180/np.pi,
}


class Grid(object):
    """
    The base class for every grid type.
    """
    # TODO: Normalize lon lat values.
    def __init__(self, grid_dict):
        self._lat_lon = None
        self._grid_dict = None
        self.__nr_coords = 2

    def __str__(self):
        name = self.__class__.__name__
        grid_dict = '\n'.join(
            '{0:s} = {1:s}'.format(
                k, str(self._grid_dict[k]))
            for k in self._grid_dict if 'vals' not in k)
        return_str = '{0:s}\n{1:s}\n{2:s}'.format(
            name, '-'*len(name), grid_dict)
        return return_str

    def __eq__(self, other):
        try:
            left = np.array(self.raw_lat_lon())
            right = np.array(other.raw_lat_lon())
        except AttributeError:
            return False
        return np.array_equal(left, right)

    def copy(self):
        return deepcopy(self)

    @property
    def len_coords(self):
        """
        Get the number of coordinates for this grid.

        Returns
        -------
        len_coords: int
            Number of coordinates for this grid.
        """
        return self.__nr_coords

    def get_coords(self):
        """
        Get the coordinates in a xarray-compatible way.

        Returns
        -------
        coords: dict(str, (str, numpy.ndarray))
            The coordinates in a xarray compatible coordinates format. The key
            is the coordinate name. The coordinates have as value a tuple with
            their own name, indicating that the they are self-describing, and
            the coordinate values as numpy array.
        """
        dim_vals = self._construct_dim()
        dim_names = self.get_coord_names()
        if isinstance(dim_vals, tuple):
            coords = {name: ((name,), dim_vals[k])
                      for k, name in enumerate(dim_names)}
        elif isinstance(dim_vals, np.ndarray):
            coords = {name: ((name,), dim_vals)
                      for k, name in enumerate(dim_names)}
        else:
            TypeError('The return value of construct dim has to be a tuple or '
                      'numpy array!')
        return coords

    @abc.abstractmethod
    def _construct_dim(self):
        pass

    @property
    def raw_dim(self):
        """
        Get the raw dimension values, as they are constructed by the grid
        description.

        Returns
        -------
        constructed_dim: tuple(numpy.ndarray) or numpy.ndarray
            The constructed dimensions. Depending on the given grid type, it is
            either a tuple of arrays or a single array.
        """
        return self._construct_dim()

    @property
    def shape(self):
        return [len(dim) for dim in self._construct_dim()]

    @property
    def lat_lon(self):
        """
        Get latitudes and longitudes for every grid point as xarray.Dataset.

        Returns
        -------
        lat_lon: xarray.Dataset
            The latitude and longitude values for every grid point as
            xarray.Dataset with latitude and longitude as variables.
        """
        if self._lat_lon is None:
            self._lat_lon = self._get_lat_lon()
        return self._lat_lon

    def _get_lat_lon(self):
        coords = self.get_coords()
        lat, lon = self._calc_lat_lon()
        ds = xr.Dataset(
            {
                'latitude': (
                    (self._grid_dict['yname'], self._grid_dict['xname']), lat),
                'longitude': (
                    (self._grid_dict['yname'], self._grid_dict['xname']), lon),
            },
            coords=coords
        )
        return ds

    @abc.abstractmethod
    def _calc_lat_lon(self):
        pass

    def raw_lat_lon(self):
        return self._calc_lat_lon()

    @staticmethod
    def normalize_lat_lon(lat, lon, data=None):
        """
        The given coordinates will be normalized and reorder into basemap
        conform coordinates. If the longitude values are between 0° and 360°,
        they will be normalized to values between -180° and 180°. Then the
        coordinates will be reorder, such that they are in an increasing order.

        Parameters
        ----------
        lat : numpy.ndarray
            The latitude values. They are representing the first data dimension.
        lon : numpy.ndarray
            The longitude values. They are representing the second data
            dimension.
        data : numpy.ndarray, xarray.DataArray or None, optional
            The data values. They will be also reordered by lat and lon. If this
            is None, only lat and lon will be reordered and returned. Default is
            None.

        Returns
        -------
        ordered_lat : numpy.ndarray
            Ordered latitude values.
        ordered_lon : numpy.ndarray
            Ordered and normalized longitude values.
        ordered_data : numpy.ndarray, xarray.DataArray or None
            The orderd data based on given latitudes and longitudes. This is
            None if no other data was given as parameter.
        """
        while np.any(lon > 180):
            lon[lon > 180] -= 360
        sort_order_lat = np.argsort(lat, 0)
        sort_order_lon = np.argsort(lon, 1)
        if data is None:
            ordered_data = None
        else:
            ordered_data = data[..., sort_order_lat, sort_order_lon]
        ordered_lat = lat[sort_order_lat, sort_order_lon]
        ordered_lon = lon[sort_order_lat, sort_order_lon]
        return ordered_lat, ordered_lon, ordered_data

    def get_coord_names(self):
        """
        Returns the name of the coordinates.

        Returns
        -------
        yname : str
            The name of the y-dimension.
        xname : str
            The name of the x-dimension
        """
        return self._grid_dict['yname'], self._grid_dict['xname']

    def _interpolate_unstructured(self, data, src_lat, src_lon,
                                  trg_lat, trg_lon, order=0):
        """
        The interpolation is done with scipy.interpolate.griddata.
        """
        if order == 1:
            method = 'linear'
        else:
            method = 'nearest'
        reshaped_data = data.reshape((-1, src_lat.size))
        unravel_shape = data.shape[:-self.len_coords]
        src_lat = src_lat.ravel()
        src_lon = src_lon.ravel()
        src_coords = np.concatenate((src_lat, src_lon), axis=1)
        unravel_shape = tuple(list(unravel_shape)+list(trg_lat.shape))
        remapped_data = np.zeros((reshaped_data.shape[0], trg_lat.size))
        trg_lat = trg_lat.ravel()
        trg_lon = trg_lon.ravel()
        trg_coords = np.concatenate((trg_lat, trg_lon), axis=1)
        for i in range(reshaped_data.shape[0]):
            sliced_array = reshaped_data[i, :]
            remapped_data[i, :] = griddata(src_coords, sliced_array, trg_coords,
                                           method=method)
        remapped_data = remapped_data.reshape(unravel_shape)
        remapped_data = np.atleast_1d(remapped_data)
        return remapped_data

    def _interpolate_structured(self, data, src_lat, src_lon,
                                trg_lat, trg_lon, order=0):
        """
        Interpolate structured data with basemap.interp function.
        """
        reshaped_data = data.reshape((-1, data.shape[-2], data.shape[-1]))
        remapped_data = np.zeros(
            (reshaped_data.shape[0], trg_lat.shape[-2], trg_lat.shape[-1]))
        for i in range(reshaped_data.shape[0]):
            sliced_array = reshaped_data[i, :, :]
            remapped_data[i, :, :] = interp(sliced_array.T, src_lat, src_lon,
                                            trg_lat, trg_lon, order=order)
        remapped_shape = list(data.shape[:-2])+list(remapped_data.shape[-2:])
        remapped_data = remapped_data.reshape(remapped_shape)
        remapped_data = np.atleast_2d(remapped_data)
        return remapped_data

    def interpolate(self, data, other_grid, order=0):
        """
        Interpolate the given data to the given other grid.

        Parameters
        ----------
        data : numpy.ndarray or xarray.DataArray
            This data is used for the  interpolation. The shape of data's grid
            axis needs to be the same as this grid.
        other_grid : Grid instance
            The other_grid is used as target grid for the interpolation.
        order : int, optional
            Specifies the interpolation order, based on basemap.interp order.
            0. order: nearest neighbour
            1. order: bilinear interpolation

        Returns
        -------
        remapped_data : numpy.ndarray or xarray.DataArray
            The remapped data with the same type as the input data. If the input
            data is a xarray.DataArray the output data will use the same
            attributes and non-grid dimensions as the input data.
        """
        if isinstance(data, xr.DataArray):
            data_values = data.values
        else:
            data_values = data
        src_lat, src_lon = self._calc_lat_lon()
        if data_values.shape[-self.len_coords:] != src_lat.shape:
            raise ValueError(
                'The last {0:d} dimensions of the data needs the same shape as '
                'the coordinates of this grid!'.format())
        src_lat, src_lon, data_values = self.normalize_lat_lon(
            src_lat, src_lon, data_values)
        try:
            trg_lat, trg_lon = other_grid.raw_lat_lon()
        except AttributeError:
            raise TypeError('other_grid has to be a child instance of Grid!')
        trg_lat, trg_lon, _ = self.normalize_lat_lon(trg_lat, trg_lon)
        if min((self.len_coords, other_grid.len_coords)) == 1:
            remapped_data = self._interpolate_unstructured(
                data_values, src_lat, src_lon, trg_lat, trg_lon, order=order)
        else:
            remapped_data = self._interpolate_structured(
                data_values, src_lat[:, 0], src_lon[0, :], trg_lat, trg_lon,
                order=order)
        if isinstance(data, xr.DataArray):
            data_dims = [dim for dim in data.dims
                         if dim not in self.get_coord_names()]
            data_coords = {dim: data.coords[dim] for dim in data_dims}
            data_coords.update(other_grid.get_coords())
            data_dims.extend(other_grid.get_coord_names())
            remapped_data = xr.DataArray(
                remapped_data,
                coords=data_coords,
                dims=data_dims,
                attrs=data.attrs
            )
        return remapped_data

    def nearest_point(self, coord):
        src_lat, src_lon = self._calc_lat_lon()
        calc_distance = distance_haversine(
            coord,
            (src_lat.flatten(), src_lon.flatten()))
        nearest_ind = np.unravel_index(calc_distance.argmin(), src_lat.shape)
        return nearest_ind

    def get_nearest_point(self, data, coord):
        """
        Get the nearest neighbour grid point for a given coordinate. The
        distance between the grid points and the given coordinates is calculated
        with the haversine formula.

        Parameters
        ----------
        data : numpy.array or xarray.DataArray
            The return value is extracted from this array. The array should have
            at least two dimensions. If the array has more than two dimensions
            the last two dimensions will be used as horizontal grid dimensions.
        coord : tuple(float, float)
            The data of the nearest grid point to this coordinate
            (latitude, longitude) will be returned. The coordinate should be in
            degree.

        Returns
        -------
        nearest_data : numpy.ndarray or xarray.DataArray
            The extracted data for the nearest neighbour grid point. The
            dimensions of this array are the same as the input data array
            without the horizontal coordinate dimensions. There is at least one
            dimension.
        """
        src_lat, src_lon = self._calc_lat_lon()
        if data.shape[-self.len_coords:] != src_lat.shape:
            raise ValueError(
                'The last two dimension of the data needs the same shape as '
                'the coordinates of this grid!')
        nearest_ind = self.nearest_point(coord)
        if self.len_coords == 1:
            nearest_data = data[..., nearest_ind[0]]
        else:
            nearest_data = data[..., nearest_ind[0], nearest_ind[1]]
        if isinstance(nearest_data, np.ndarray):
            nearest_data = np.atleast_1d(nearest_data)
        return nearest_data

    @abc.abstractmethod
    def lonlatbox(self, data, ll_box):
        """
        Slice a lonlatbox from the given data.
        """
        pass

    def _lonlatbox(self, data, ll_box, unstructured=False):
        """
        The data is sliced as grid with given lonlat box.

        Parameters
        ----------
        data : numpy.ndarray or xarray.DataArray
            The data which should be sliced. The shape of the last two
            dimensions should be the same as the grid dimensions.
        ll_box : tuple(float)
            The longitude and latitude box with four entries as degree. The
            entries are handled in the following way:
                (left/west, top/north, right/east, bottom/south)
        unstructured : bool, optional
            If the output grid should be unstructured.

        Returns
        -------
        sliced_data : numpy.ndarray or xarray.DataArray
            The sliced data with the same type as the input data. If the input
            data is a xarray.DataArray the output data will use the same
            attributes and non-grid dimensions as the input data.
        sliced_grid : Grid
            A new child instance of Grid with the sliced coordinates as values.
        """
        if isinstance(data, xr.DataArray):
            data_values = data.values
        else:
            data_values = data
        src_lat, src_lon = self._calc_lat_lon()
        if data_values.shape[-self.len_coords:] != src_lat.shape:
            raise ValueError(
                'The last two dimension of the data needs the same shape as '
                'the coordinates of this grid!')
        if unstructured:
            sliced_data, new_grid_dict = self._unstructured_box(data_values,
                                                                ll_box)
        else:
            sliced_data, new_grid_dict = self._structured_box(data_values,
                                                              ll_box)
        sliced_grid = pymepps.GridBuilder(new_grid_dict).build_grid()
        if isinstance(data, xr.DataArray):
            data_dims = [dim for dim in data.dims
                         if dim not in self.get_coord_names()]
            data_coords = {dim: data.coords[dim] for dim in data_dims}
            data_coords.update(sliced_grid.get_coords())
            data_dims.extend(sliced_grid.get_coord_names())
            sliced_data = xr.DataArray(
                sliced_data,
                coords=data_coords,
                dims=data_dims,
                attrs=data.attrs
            )
        return sliced_data, sliced_grid

    def _structured_box(self, data, ll_box):
        calc_lat, calc_lon = self._construct_dim()
        if not len(ll_box) == 4:
            raise ValueError(
                'The latitude-longitude box doesn\'t have a length of 4, '
                'instead the length is: {0:d}'.format(len(ll_box)))
        lon_box = (ll_box[0], ll_box[2])
        lat_box = (ll_box[1], ll_box[3])
        lat_bound = np.logical_and(
            calc_lat >= np.min(lat_box), calc_lat <= np.max(lat_box)
        )
        lon_bound = np.logical_and(
            calc_lon >= np.min(lon_box), calc_lon <= np.max(lon_box)
        )
        sliced_data = data[..., lat_bound, :][..., lon_bound]

        lat_vals = calc_lat[lat_bound]
        lon_vals = calc_lon[lon_bound]

        new_grid_dict = deepcopy(self._grid_dict)
        new_grid_dict['ysize'] = len(lat_vals)
        new_grid_dict['xsize'] = len(lon_vals)
        new_grid_dict['yvals'] = list(lat_vals)
        new_grid_dict['xvals'] = list(lon_vals)
        keys_to_del = ['yfirst', 'yinc', 'xfirst', 'xinc']
        [new_grid_dict.pop(k, None) for k in keys_to_del]
        return sliced_data, new_grid_dict

    def _unstructured_box(self, data, ll_box):
        calc_lat, calc_lon = self._calc_lat_lon()
        if data.shape[-self.len_coords:] != calc_lat.shape:
            raise ValueError(
                'The last dimension(s) of the data needs the same shape as '
                'the coordinates of this grid!')
        if not len(ll_box) == 4:
            raise ValueError(
                'The latitude-longitude box doesn\'t have a length of 4, '
                'instead the length is: {0:d}'.format(len(ll_box)))
        lon_box = (ll_box[0], ll_box[2])
        lat_box = (ll_box[1], ll_box[3])
        bound = np.all((
            calc_lat >= np.min(lat_box),
            calc_lat <= np.max(lat_box),
            calc_lon >= np.min(lon_box),
            calc_lon <= np.max(lon_box)
        ), axis=0)
        if np.sum(bound) == 0:
            raise ValueError('Only an empty array remains, please choose '
                             'another longitude-latitude box!')
        sliced_data = data[..., bound]

        lat_vals = calc_lat[bound]
        lon_vals = calc_lon[bound]

        # Construct a unstructured grid
        new_grid_dict = dict(
            gridtype='unstructured',
            xlongname='longitude',
            xname='lon',
            xunits='degrees',
            ylongname='latitude',
            yname='lat',
            yunits='degrees',)
        new_grid_dict['gridsize'] = len(lat_vals)
        new_grid_dict['yvals'] = list(lat_vals)
        new_grid_dict['xvals'] = list(lon_vals)
        return sliced_data, new_grid_dict

    @staticmethod
    def convert_to_deg(field, unit):
        """
        Method to convert given field with given unit into degree.

        Parameters
        ----------
        field
        unit

        Returns
        -------

        """
        try:
            calculated_field = [known_units[known](field)
                                for known in known_units
                                if known in unit.lower()][0]
        except IndexError:
            raise ValueError('There is no calculating rule for the given unit '
                             '{0:s} defined yet!'.format(unit))
        return calculated_field

def distance_haversine(p1, p2):
    """
    Calculate the great circle distance between two points 
    on the earth. The formula is based on the haversine formula [1]_.

    Parameters
    ----------
    p1 : tuple (array_like, array_like)
        The coordinates (latitude, longitude) of the first point in degrees.
    p2 : tuple (array_like, array_like)
        The coordinates (latitude, longitude) of the second point in degrees.
        
    Returns
    -------
    d : float
        The calculated haversine distance in meters.
    
    Notes
    -----
    Script based on: http://stackoverflow.com/a/29546836
    
    References
    ----------
    .. [1] de Mendoza y Ríos, Memoria sobre algunos métodos nuevos de calcular
       la longitud por las distancias lunares: y aplication de su teórica á la
       solucion de otros problemas de navegacion, 1795.
    """
    lat1, lon1 = p1
    lat2, lon2 = p2
    R = 6371E3
    lat1, lon1, lat2, lon2 = map(np.deg2rad, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    d = R * c
    return d
