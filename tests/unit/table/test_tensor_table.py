#
# Copyright (c) 2023, NVIDIA CORPORATION.
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
from typing import List, Tuple, Type

import pytest

from merlin.core.compat import HAS_GPU, cudf
from merlin.core.compat import cupy as cp
from merlin.core.compat import numpy as np
from merlin.core.compat.tensorflow import tensorflow as tf
from merlin.core.compat.torch import torch as th
from merlin.core.dispatch import df_from_dict, dict_from_df, make_df
from merlin.core.protocols import DictLike, Transformable
from merlin.dag import BaseOperator, ColumnSelector
from merlin.schema import ColumnSchema, Schema
from merlin.table import CupyColumn, Device, NumpyColumn, TensorflowColumn, TensorTable, TorchColumn
from tests.conftest import assert_eq

col_type: List[Type] = []
cpu_target_packages: List[Tuple] = []
gpu_target_packages: List[Tuple] = []
gpu_source_col: List[Tuple] = []
cpu_source_col: List[Tuple] = []

if np:
    tensor_dict = {
        "a__values": np.array([1, 2, 3]),
        "a__offsets": np.array([0, 1, 3]),
    }
    col_type.append(NumpyColumn)
    cpu_target_packages.append((NumpyColumn, tensor_dict))
    cpu_source_col.append((NumpyColumn, np.array, np))

if cp and HAS_GPU:
    tensor_dict = {
        "a__values": cp.asarray([1, 2, 3]),
        "a__offsets": cp.asarray([0, 1, 3]),
    }
    col_type.append(CupyColumn)
    gpu_target_packages.append((CupyColumn, tensor_dict))
    gpu_source_col.append((CupyColumn, cp.asarray, cp))

if tf and HAS_GPU:
    with tf.device("/CPU"):
        tensor_dict_cpu = {
            "a__values": tf.convert_to_tensor(np.array([1, 2, 3])),
            "a__offsets": tf.convert_to_tensor(np.array([0, 1, 3])),
        }
    with tf.device("/GPU:0"):
        tensor_dict_gpu = {
            "a__values": tf.convert_to_tensor(np.array([1, 2, 3])),
            "a__offsets": tf.convert_to_tensor(np.array([0, 1, 3])),
        }
    cpu_target_packages.append((TensorflowColumn, tensor_dict_cpu))
    gpu_target_packages.append((TensorflowColumn, tensor_dict_gpu))
    col_type.append(TensorflowColumn)

if th and HAS_GPU:
    tensor_dict_cpu = {
        "a__values": th.tensor([1, 2, 3], dtype=th.int32),
        "a__offsets": th.tensor([0, 1, 3], dtype=th.int32),
    }
    tensor_dict_gpu = {
        "a__values": th.tensor([1, 2, 3], dtype=th.int32).cuda(),
        "a__offsets": th.tensor([0, 1, 3], dtype=th.int32).cuda(),
    }
    cpu_target_packages.append((TorchColumn, tensor_dict_cpu))
    gpu_target_packages.append((TorchColumn, tensor_dict_gpu))
    col_type.append(TorchColumn)


@pytest.mark.parametrize("protocol", [DictLike, Transformable])
def test_tensortable_match_protocol(protocol):
    obj = TensorTable()

    assert isinstance(obj, protocol)


@pytest.mark.parametrize("col_type", col_type)
def test_tensortable_from_framework_arrays(col_type):
    constructor = col_type.array_constructor()

    tensor_dict = {
        "a": constructor([1, 2, 3]),
        "b": constructor([3, 4, 5, 6]),
        "c": constructor([5, 6, 7]),
    }

    table = TensorTable(tensor_dict)
    assert isinstance(table, TensorTable)
    for column in table.columns:
        assert isinstance(table[column], col_type)


def test_tensortable_with_ragged_columns():
    tensor_dict = {
        "a__values": np.array([1, 2, 3]),
        "a__offsets": np.array([0, 1, 3]),
    }

    table = TensorTable(tensor_dict)
    assert table.columns == ["a"]
    assert all(table["a"].offsets == tensor_dict["a__offsets"])


@pytest.mark.skipif(
    tf is None, reason="Tensorflow is required for cross-framework validation tests"
)
def test_column_type_validation():
    tensor_dict = {
        "a__values": np.array([1, 2, 3]),
        "a__offsets": np.array([0, 1, 3]),
        "b": tf.constant([4, 5, 6]),
    }

    with pytest.raises(TypeError) as exc_info:
        TensorTable(tensor_dict)

    assert "from the same framework" in str(exc_info)


def test_column_type_property():
    tensor_dict = {
        "a__values": np.array([1, 2, 3]),
        "a__offsets": np.array([0, 1, 3]),
    }

    assert TensorTable(tensor_dict).column_type == NumpyColumn


@pytest.mark.skipif(
    not (tf and HAS_GPU),
    reason="both TensorFlow and CUDA GPUs are required for cross-framework validation tests",
)
def test_column_device_validation():
    with tf.device("/CPU"):
        tensor_dict_cpu = {
            "a__values": tf.convert_to_tensor(np.array([1, 2, 3])),
            "a__offsets": tf.convert_to_tensor(np.array([0, 1, 3])),
        }
    with tf.device("/GPU:0"):
        tensor_dict_gpu = {
            "b__values": tf.convert_to_tensor(np.array([1, 2, 3])),
            "b__offsets": tf.convert_to_tensor(np.array([0, 1, 3])),
        }

    tensor_dict = {**tensor_dict_cpu, **tensor_dict_gpu}

    with pytest.raises(ValueError) as exc_info:
        TensorTable(tensor_dict)

    assert "on the same device" in str(exc_info)


class PaddingOperator(BaseOperator):
    def __init__(self, length=None, array_lib=np):
        self.length = length
        self.array_lib = array_lib

    def transform(self, col_selector, transformable):
        for col_name, col_data in transformable[col_selector.names].items():
            # dtype = col_data.dtype.to("numpy")

            dtype = self.array_lib.int32
            num_rows = len(col_data.offsets) - 1
            result = self.array_lib.zeros((num_rows, self.length), dtype=dtype)

            for i in range(num_rows):
                row_length = len(col_data[i])
                padding = self.array_lib.array([0] * (self.length - row_length), dtype=dtype)
                padded_row = self.array_lib.append(col_data[i], padding)
                result[i] = padded_row.astype(dtype)
            transformable[col_name] = type(col_data)(result)

        return transformable

    # TODO: Define what this op supports (and doesn't)


# target input, target column
# source input, source column
@pytest.mark.parametrize("source_column", cpu_source_col)
@pytest.mark.parametrize("target_column", cpu_target_packages)
def test_tensor_cpu_table_operator(source_column, target_column):
    source_column_type, source_col_constructor, array_lib = source_column
    target_column_type, target_input = target_column
    op = PaddingOperator(3, array_lib=array_lib)
    expected_output = source_col_constructor([[1, 0, 0], [2, 3, 0]])

    tensor_table = TensorTable(target_input)

    # Column conversions would happen in the executor
    tensor_table = tensor_table.as_tensor_type(source_column_type)

    result = op.transform(ColumnSelector(["a"]), tensor_table)

    # Column conversions would happen in the executor
    result = result.as_tensor_type(target_column_type)

    # Check the results
    assert isinstance(result, TensorTable)
    for column in result.values():
        assert isinstance(column, target_column_type)

    assert result["a"].values.shape == expected_output.shape
    results = result["a"].values
    results = results.numpy() if hasattr(results, "numpy") else results
    assert np.array_equal(results, expected_output)


@pytest.mark.skipif(not cp, reason="cupy not available")
@pytest.mark.parametrize("source_column", gpu_source_col)
@pytest.mark.parametrize("target_column", gpu_target_packages)
def test_tensor_gpu_table_operator(source_column, target_column):
    source_column_type, source_col_constructor, array_lib = source_column
    target_column_type, target_input = target_column
    op = PaddingOperator(3, array_lib=array_lib)
    expected_output = source_col_constructor([[1, 0, 0], [2, 3, 0]])

    tensor_table = TensorTable(target_input)

    # Column conversions would happen in the executor
    tensor_table = tensor_table.as_tensor_type(source_column_type)

    # Executor runs the ops
    result = op.transform(ColumnSelector(["a"]), tensor_table)

    # Column conversions would happen in the executor
    result = result.as_tensor_type(target_column_type)

    # Check the results
    assert isinstance(result, TensorTable)
    for column in result.values():
        assert isinstance(column, target_column_type)

    assert result["a"].values.shape == expected_output.shape
    results = result["a"].values
    results = results.cpu() if hasattr(results, "cpu") else results
    results = results.numpy() if hasattr(results, "numpy") else cp.asnumpy(results)
    assert np.array_equal(results, cp.asnumpy(expected_output.get()))


def test_to_dict():
    tensor_dict = {
        "a__values": np.array([1, 2, 3]),
        "a__offsets": np.array([0, 1, 3]),
    }

    table = TensorTable(tensor_dict)

    assert table.to_dict() == tensor_dict


@pytest.mark.parametrize("device", [None, "cpu"] if HAS_GPU else ["cpu"])
def test_df_to_tensor_table(device):
    df = make_df({"a": [[1, 2, 3], [4, 5, 6, 7]], "b": [1, 2]}, device=device)

    table = TensorTable.from_df(df)
    roundtrip_df = table.to_df()

    assert isinstance(table, TensorTable)
    expected_device = Device.CPU if device else Device.GPU
    assert table.device == expected_device

    assert_eq(df, roundtrip_df)


@pytest.mark.parametrize("device", [None, "cpu"] if HAS_GPU else ["cpu"])
def test_df_to_dict(device):
    df = make_df({"a": [[1, 2, 3], [4, 5, 6, 7]], "b": [1, 2]}, device=device)

    df_dict = dict_from_df(df)
    roundtrip_df = df_from_dict(df_dict)

    assert isinstance(df_dict, dict)
    assert_eq(df, roundtrip_df)


@pytest.mark.skipif(cp is None or not HAS_GPU, reason="requires GPU and CuPy")
def test_cpu_transfer():
    tensor_dict = {
        "a__values": cp.array([1, 2, 3]),
        "a__offsets": cp.array([0, 1, 3]),
    }

    gpu_table = TensorTable(tensor_dict)
    cpu_table = gpu_table.cpu()

    assert cpu_table.device == Device.CPU
    assert isinstance(list(cpu_table.values())[0], NumpyColumn)


@pytest.mark.skipif(cp is None or not HAS_GPU, reason="requires GPU and CuPy")
def test_gpu_transfer():
    tensor_dict = {
        "a__values": np.array([1, 2, 3]),
        "a__offsets": np.array([0, 1, 3]),
    }

    cpu_table = TensorTable(tensor_dict)
    gpu_table = cpu_table.gpu()

    assert gpu_table.device == Device.GPU
    assert isinstance(list(cpu_table.values())[0], NumpyColumn)


def test_as_tensor_type_invalid_type():
    table = TensorTable({"a": np.array([1, 2, 3])})
    with pytest.raises(ValueError) as exc_info:
        table.as_tensor_type("not_a_type")
    assert "tensor_type argument must be a type" in str(exc_info.value)


def test_as_tensor_type_unsupported_type():
    table = TensorTable({"a": np.array([1, 2, 3])})
    with pytest.raises(ValueError) as exc_info:
        table.as_tensor_type(np.ndindex)
    assert "Unsupported tensor type" in str(exc_info.value)


class TestTensorTableFromDf:
    def test_default(self):
        df = make_df(
            {
                "scalar": [0.1, 0.2],
                "fixed_list": [[1, 2], [3, 4]],
                "ragged_list": [[1, 2], [3]],
            }
        )
        table = TensorTable.from_df(df)
        xp = cp if cudf and isinstance(df, cudf.DataFrame) else np
        xp.testing.assert_array_equal(
            table["fixed_list"].values, xp.array([1, 2, 3, 4], dtype="int64")
        )
        xp.testing.assert_array_equal(
            table["fixed_list"].offsets, xp.array([0, 2, 4], dtype="int32")
        )
        xp.testing.assert_array_equal(
            table["ragged_list"].values, xp.array([1, 2, 3], dtype="int64")
        )
        xp.testing.assert_array_equal(
            table["ragged_list"].offsets, xp.array([0, 2, 3], dtype="int32")
        )
        xp.testing.assert_array_equal(table["scalar"].values, xp.array([0.1, 0.2], dtype="float64"))
        assert table["scalar"].offsets is None

    def test_with_schema_ragged(self):
        df = make_df({"feature": [[1, 2], [3, 4]]})
        schema = Schema([ColumnSchema("feature", dims=(None, None))])
        table = TensorTable.from_df(df, schema=schema)
        xp = cp if cudf and isinstance(df, cudf.DataFrame) else np
        xp.testing.assert_array_equal(
            table["feature"].values, xp.array([1, 2, 3, 4], dtype="int64")
        )
        xp.testing.assert_array_equal(table["feature"].offsets, xp.array([0, 2, 4], dtype="int32"))

    def test_with_schema_ragged_error(self):
        df = make_df({"feature": [[1, 2], [3]]})
        schema = Schema([ColumnSchema("feature", dims=(None, 2))])
        with pytest.raises(ValueError) as exc_info:
            TensorTable.from_df(df, schema=schema)
        assert "ColumnSchema for list column 'feature' describes a fixed size list" in str(
            exc_info.value
        )

    def test_with_schema_fixed(self):
        df = make_df({"feature": [[1, 2], [3, 4]]})
        schema = Schema([ColumnSchema("feature", dims=(None, 2))])
        table = TensorTable.from_df(df, schema=schema)
        xp = cp if cudf and isinstance(df, cudf.DataFrame) else np
        xp.testing.assert_array_equal(
            table["feature"].values, xp.array([[1, 2], [3, 4]], dtype="int64")
        )
        assert table["feature"].offsets is None
