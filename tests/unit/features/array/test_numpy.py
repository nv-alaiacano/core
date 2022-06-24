#
# Copyright (c) 2022, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import pytest

from merlin.features.array.compat import cudf, cupy, numpy, pandas, tensorflow
from merlin.features.array.numpy import MerlinNumpyArray
from merlin.features.df import VirtualDataframe

pytest.importorskip("numpy")


@pytest.mark.skipif(numpy is None, reason="Numpy is not defined")
def test_np_array_to_merlin_numpy_array():
    np_array = numpy.array([1, 2, 3, 4])
    merlin_np_array = MerlinNumpyArray(np_array)

    assert isinstance(merlin_np_array.array, numpy.ndarray)
    assert (merlin_np_array.array == np_array).all()


@pytest.mark.skipif(cupy is None, reason="Cupy is not defined")
def test_cupy_array_to_merlin_numpy_array():
    cp_array = cupy.array([1, 2, 3, 4])
    merlin_np_array = MerlinNumpyArray(cp_array)

    assert isinstance(merlin_np_array.array, numpy.ndarray)
    assert (merlin_np_array.array == cupy.asnumpy(cp_array)).all()


@pytest.mark.skipif(cudf is None, reason="Cudf is not defined")
def test_cudf_series_to_merlin_numpy_array():
    cudf_series = cudf.Series([1, 2, 3, 4])
    merlin_np_array = MerlinNumpyArray(cudf_series)

    assert isinstance(merlin_np_array.array, numpy.ndarray)
    assert (merlin_np_array.array == cudf_series.to_numpy()).all()


@pytest.mark.skipif(pandas is None, reason="Pandas is not defined")
def test_pandas_series_to_merlin_numpy_array():
    pandas_series = pandas.Series([1, 2, 3, 4])
    merlin_numpy_array = MerlinNumpyArray(pandas_series)

    assert isinstance(merlin_numpy_array.array, numpy.ndarray)
    assert (merlin_numpy_array.array == pandas_series.to_numpy()).all()


@pytest.mark.skipif(tensorflow is None, reason="Tensorflow is not defined")
def test_tf_tensor_to_merlin_numpy_array():
    tf_tensor = tensorflow.random.uniform((10,))
    merlin_np_array = MerlinNumpyArray(tf_tensor)

    assert isinstance(merlin_np_array.array, numpy.ndarray)
    assert (merlin_np_array.array == tf_tensor.numpy()).all()


def test_virtual_df_convert_to_numpy():
    dict_array = {
        "a": numpy.array([1, 2, 3, 4, 5]),
        "b": numpy.array([1, 2, 3, 4, 5]),
        "c": numpy.array([1, 2, 3, 4, 5]),
    }
    vdf = VirtualDataframe(dict_array)
    assert isinstance(vdf, VirtualDataframe)

    m_vdf = vdf.columns_to(numpy.ndarray)

    for col_name in m_vdf.columns:
        assert isinstance(m_vdf[col_name], numpy.ndarray)


def test_virtual_df_convert_from_numpy():
    dict_array = {
        "a": numpy.array([1, 2, 3, 4, 5]),
        "b": numpy.array([1, 2, 3, 4, 5]),
        "c": numpy.array([1, 2, 3, 4, 5]),
    }
    vdf = VirtualDataframe(dict_array)
    assert isinstance(vdf, VirtualDataframe)

    m_vdf = vdf.columns_to(numpy.ndarray)

    for col_name in m_vdf.columns:
        assert isinstance(m_vdf[col_name], numpy.ndarray)