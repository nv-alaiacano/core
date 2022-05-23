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

import cudf
import cupy as cp
import numpy as np
import tensorflow as tf

from merlin.features.array.tensorflow import MerlinTensorflowArray


def test_np_array_to_merlin_tf_array():
    np_array = np.array([1, 2, 3, 4])
    merlin_tf_array = MerlinTensorflowArray(np_array)

    assert isinstance(merlin_tf_array.array, tf.Tensor)
    assert (merlin_tf_array.array.numpy() == np_array).all()


def test_cupy_array_to_merlin_tf_array():
    cp_array = cp.array([1, 2, 3, 4])
    merlin_tf_array = MerlinTensorflowArray(cp_array)

    assert isinstance(merlin_tf_array.array, tf.Tensor)
    assert (merlin_tf_array.array.numpy() == cp.asnumpy(cp_array)).all()


def test_cudf_series_to_merlin_tf_array():
    cudf_series = cudf.Series([1, 2, 3, 4])
    merlin_tf_array = MerlinTensorflowArray(cudf_series)

    assert isinstance(merlin_tf_array.array, tf.Tensor)
    assert (merlin_tf_array.array.numpy() == cudf_series.to_numpy()).all()


def test_tf_tensor_to_merlin_tf_array():
    tf_tensor = tf.random.uniform((10,))
    merlin_tf_array = MerlinTensorflowArray(tf_tensor)

    assert isinstance(merlin_tf_array.array, tf.Tensor)
    assert (merlin_tf_array.array.numpy() == tf_tensor.numpy()).all()