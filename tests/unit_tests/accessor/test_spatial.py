#!/bin/env python
# -*- coding: utf-8 -*-
#
# Created on 06.07.17
#
# Created for pymepps
#
# @author: Tobias Sebastian Finn, tobias.sebastian.finn@studium.uni-hamburg.de
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
import os
import unittest
import logging
import datetime

# External modules
import xarray as xr
import numpy as np
import pandas.util.testing as pdt

# Internal modules
import pymepps.accessor
from pymepps.loader.datasets.spatialdataset import SpatialDataset
from pymepps.loader.filehandler.netcdfhandler import NetCDFHandler
from pymepps.grid import GridBuilder


BASE_PATH = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)))),
    'data')

logging.basicConfig(level=logging.DEBUG)


class TestSpatial(unittest.TestCase):
    def setUp(self):
        file = os.path.join(BASE_PATH, 'spatial', 'raw',
                            'GFS_Global_0p25deg_20161219_0600.nc')
        ds = SpatialDataset(NetCDFHandler(file),)
        self.array = xr.open_dataarray(file)
        self.grid = ds.get_grid(
            'Maximum_temperature_height_above_ground_Mixed_intervals_Maximum',
            data_array=self.array)

    def tearDown(self):
        try:
            os.remove('test.nc')
        except FileNotFoundError:
            pass

    def test_array_has_accessor(self):
        self.assertTrue(hasattr(self.array, 'pp'))

    def test_accessor_has_array_as_data(self):
        self.assertEqual(id(self.array.pp.data), id(self.array))

    def test_grid_returns_grid(self):
        self.array.pp.grid = self.grid
        self.assertEqual(self.array.pp._grid, self.array.pp.grid)

    def test_str_returns_right(self):
        name = "{0:s}({1:s})".format(self.array.pp.__class__.__name__,
                                     self.array.name)
        test_str = "{0:s}\n{1:s}\nGrid: {1:s}".format(
            name, '-'*len(name), str(None))
        self.assertEqual(test_str, str(self.array.pp))

    def test_grid_could_set(self):
        self.assertEqual(self.array.pp._grid, None)
        self.array.pp.grid = self.grid
        self.assertEqual(self.array.pp._grid, self.grid)

    def test_grid_set_raises_type_error_if_wrong_type(self):
        with self.assertRaises(TypeError):
            self.array.pp.grid = self.array

    def test_check_data_coords_raises_typeerror_if_no_grid(self):
        with self.assertRaises(TypeError):
            self.array.pp._check_data_coordinates(self.array)

    def test_check_data_coords_returns_item(self):
        self.array.pp.grid = self.grid
        return_item = self.array.pp._check_data_coordinates(self.array)
        xr.testing.assert_identical(return_item, self.array)

    def test_check_data_coords_raises_valueerror_if_wrong_coords(self):
        self.array.pp.grid = self.grid
        test_array = self.array[:, :, :5, :5]
        with self.assertRaises(ValueError):
            self.array.pp._check_data_coordinates(test_array)

    def test_merge_checks_input(self):
        test_array = self.array[:, :, :5, :5]
        test_array.pp._grid = self.grid
        with self.assertRaises(ValueError):
            test_array.pp.merge(self.array)
        self.array.pp.grid = self.grid
        self.array.pp.merge()
        with self.assertRaises(ValueError):
            self.array.pp.merge(test_array)

    def test_merge_returns_merged_array(self):
        test_array = self.array.copy()
        test_array.name = 'test'
        test_dataset = xr.merge([test_array, self.array])
        merged_array = test_dataset.to_array(name='merged_array')
        self.array.pp.grid = self.grid
        returned_array = self.array.pp.merge(test_array)
        np.testing.assert_equal(merged_array.values, returned_array.values)

    def test_merge_merged_array_has_same_grid(self):
        test_array = self.array.copy()
        test_array.name = 'test'
        self.array.pp.grid = self.grid
        merged_array = self.array.pp.merge(test_array)
        self.assertIsNotNone(merged_array.pp.grid)
        self.assertEqual(id(self.grid), id(merged_array.pp.grid))

    def test_update_checks_input(self):
        test_array = self.array[:, :, :5, :5]
        test_array.pp._grid = self.grid
        with self.assertRaises(ValueError):
            test_array.pp.update(self.array)
        self.array.pp.grid = self.grid
        self.array.pp.update()
        with self.assertRaises(ValueError):
            self.array.pp.update(test_array)

    def test_update_add_data_to_coords(self):
        test_array = self.array.copy()
        test_array['time'] = [datetime.datetime.utcnow(), ]
        concatenated_array = xr.concat([self.array, test_array], dim='time')
        self.array.pp.grid = self.grid
        updated_array = self.array.pp.update(test_array)
        np.testing.assert_equal(updated_array.values, concatenated_array.values)

    def test_update_updates_data(self):
        test_array = self.array.copy()
        test_array[:] = 5
        self.array.pp.grid = self.grid
        updated_array = self.array.pp.update(test_array)
        self.assertTrue(np.all(updated_array == 5))

    def test_update_raises_error_if_concat_is_not_working(self):
        test_array = self.array.copy()
        test_array[:] = 5
        del test_array['time']
        self.array.pp.grid = self.grid
        with self.assertRaises(TypeError):
            _ = self.array.pp.update(test_array)

    def test_update_updated_array_has_same_grid(self):
        test_array = self.array.copy()
        test_array[:] = 5
        self.array.pp.grid = self.grid
        updated_array = self.array.pp.update(test_array)
        self.assertIsNotNone(updated_array.pp.grid)
        self.assertEqual(id(self.grid), id(updated_array.pp.grid))

    def test_set_grid_cooordinates_returns_grid_array(self):
        self.array.pp._grid = self.grid
        returned_array = self.array.pp.set_grid_coordinates()
        self.assertEqual(id(returned_array.pp.grid), id(self.grid))

    def test_set_grid_coordinates_sets_names(self):
        self.array = self.array.rename({'lat': 'y', 'lon': 'x'})
        old_dim_names = np.array(self.array.dims)
        true_dim_names = list(old_dim_names[:-2]) + ['lat', 'lon']
        self.array.pp._grid = self.grid
        np.testing.assert_equal(np.array(self.array.dims), old_dim_names)
        gridded_array = self.array.pp.set_grid_coordinates()
        np.testing.assert_equal(np.array(gridded_array.dims), true_dim_names)

    def test_set_grid_coordinates_sets_values(self):
        coord_values = self.grid.raw_dim
        self.array['lat'] = np.arange(self.array['lat'].size)
        self.array['lon'] = np.arange(self.array['lon'].size)
        self.assertFalse(any([
            np.all(np.equal(self.array[dim].values, coord_values[num]))
            for num, dim in enumerate(self.array.dims[-2:])])
        )
        self.array.pp._grid = self.grid
        self.array = self.array.pp.set_grid_coordinates()
        self.assertTrue(all([
            np.all(np.equal(self.array[dim].values, coord_values[num]))
            for num, dim in enumerate(self.array.dims[-2:])])
        )

    def test_merge_analysis_timedelta_merges_times(self):
        test_array = self.array.copy()
        test_array = test_array.expand_dims('runtime')
        test_array.coords['runtime'] = [datetime.datetime.now(), ]
        test_array = test_array.rename({'time': 'validtime'})
        test_array['validtime'] = test_array['validtime'].values - \
                                  test_array['runtime'].values
        merged_array = test_array.pp.merge_analysis_timedelta()
        np.testing.assert_equal(merged_array.dims, self.array.dims)
        np.testing.assert_equal(merged_array.values, self.array.values)

    def test_to_pandas_no_lonlat_given_returns_stacked_dataframe(self):
        stacked_array = self.array.stack(col=self.array.dims[1:])
        target_df = stacked_array.to_pandas()
        returned_df = self.array.pp.to_pandas()
        # Trick to speed up the whole thing
        pdt.assert_frame_equal(target_df.T, returned_df.T, check_dtype=False)

    def test_to_pandas_lonlat_given_returns_point_dataframe(self):
        self.array.pp.grid = self.grid
        returned_df = self.array.pp.to_pandas((10, 53.5))
        self.array = self.array.sel(lat=53.5).sel(lon=10)
        stacked_array = self.array.stack(col=self.array.dims[1:])
        target_df = stacked_array.to_pandas()
        pdt.assert_frame_equal(target_df, returned_df, check_dtype=False)

    def test_remapnn_interpolates_with_nearest_neighbour_approach(self):
        file = os.path.join(BASE_PATH, 'grids', 'gaussian_y')
        builder = GridBuilder(file)
        gaussian_grid = builder.build_grid()
        self.array.pp.grid = self.grid
        returned_array = self.array.pp.remapnn(gaussian_grid)
        remapped_array = self.grid.interpolate(self.array, gaussian_grid, 0)
        remapped_array.pp.grid = gaussian_grid
        xr.testing.assert_equal(returned_array, remapped_array)

    def test_remapbil_interpolates_with_nearest_neighbour_approach(self):
        file = os.path.join(BASE_PATH, 'grids', 'gaussian_y')
        builder = GridBuilder(file)
        gaussian_grid = builder.build_grid()
        self.array.pp.grid = self.grid
        returned_array = self.array.pp.remapbil(gaussian_grid)
        remapped_array = self.grid.interpolate(self.array, gaussian_grid, 1)
        remapped_array.pp.grid = gaussian_grid
        xr.testing.assert_equal(returned_array, remapped_array)

    def test_lonlatbox_slices_lonlatbox_from_array(self):
        lonlatbox = (9, 55, 12, 52)
        self.array.pp.grid = self.grid.copy()
        returned_array = self.array.pp.sellonlatbox(lonlatbox)
        sliced_array, sliced_grid = self.grid.lonlatbox(self.array, lonlatbox)
        sliced_array.pp.grid = sliced_grid
        xr.testing.assert_equal(returned_array, sliced_array)
        self.assertEqual(sliced_grid, returned_array.pp.grid)

    def test_save_creates_new_nc_file(self):
        self.assertFalse(os.path.isfile('test.nc'))
        self.array.pp.save('test.nc')
        self.assertTrue(os.path.isfile('test.nc'))

    def test_save_saves_same_data(self):
        self.array.pp.save('test.nc')
        opened_array = xr.open_dataarray('test.nc')
        xr.testing.assert_equal(opened_array, self.array)

    def test_save_saves_also_grid(self):
        self.array.pp.grid = self.grid
        self.array.pp.save('test.nc')
        opened_array = xr.open_dataarray('test.nc')
        grid_attrs = {attr[5:]: opened_array.attrs[attr]
                      for attr in opened_array.attrs if attr[:5] == 'grid_'}
        opened_grid = GridBuilder(grid_attrs).build_grid()
        self.assertEqual(self.grid, opened_grid)


if __name__ == '__main__':
    unittest.main()
