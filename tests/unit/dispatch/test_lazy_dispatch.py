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

from merlin.dispatch.lazy import lazy_singledispatch

try:
    import tensorflow as tf
except ImportError:
    tf = None


return_type_name = lazy_singledispatch("return_type_name")


@return_type_name.register
def return_int(arg: int):
    return "int"


@return_type_name.register
def return_float(arg: float):
    return "float"


@return_type_name.register_lazy("tensorflow")
def register_tf_to_array():
    import tensorflow as tf  # pylint:disable=reimported

    @return_type_name.register(tf.Tensor)
    def return_tensor(arg: tf.Tensor):
        return "tensor"


@pytest.mark.skipif(not tf, reason="requires tensorflow")
def test_lazy_dispatch():
    result = return_type_name(5)
    assert result == "int"

    result = return_type_name(5.0)
    assert result == "float"

    result = return_type_name(tf.constant([1, 2, 3, 4]))
    assert result == "tensor"

    with pytest.raises(NotImplementedError) as exc:
        result = return_type_name("abc")
    assert "doesn't have a registered implementation" in str(exc.value)
