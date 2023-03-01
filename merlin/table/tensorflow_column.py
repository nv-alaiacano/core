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
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Tuple, Type, Union

from merlin.core.compat import tensorflow as tf
from merlin.table.conversions import _from_dlpack_cpu, _from_dlpack_gpu, _to_dlpack
from merlin.table.tensor_column import Device, TensorColumn


class DlpackDevice(Enum):
    CPU = 1
    CUDA = 2


@dataclass(frozen=True)
class TensorflowDlpackWrapper:
    capsule: Any
    device: Tuple[DlpackDevice, int]

    def __dlpack__(self, stream: Optional[Union[int, Any]] = None):
        # TODO: Figure out what if anything we can do with a stream here
        return self.capsule

    def __dlpack_device__(self):
        device = (self.device[0].value, int(self.device[1]))
        return device


class TensorflowColumn(TensorColumn):
    """
    A SeriesLike column backed by Tensorflow tensors
    """

    @classmethod
    def array_type(cls) -> Type:
        """
        The type of the arrays backing this column
        """
        return tf.Tensor

    @classmethod
    def supported_devices(cls):
        """
        List of device types supported by this column type
        """
        return [Device.CPU, Device.GPU]

    def __init__(self, values: "tf.Tensor", offsets: "tf.Tensor" = None, dtype=None, _ref=None):
        values_device = self._tf_device(values)

        if offsets is not None:
            offsets_device = self._tf_device(offsets)
            if values_device != offsets_device:
                raise ValueError(
                    f"Values and offsets were detected on different devices: "
                    f"values ({values_device}) and offsets ({offsets_device})."
                )

        super().__init__(values, offsets, dtype, _device=values_device, _ref=_ref)

    def _tf_device(self, tensor):
        return Device.GPU if "GPU" in tensor.device else Device.CPU


@_to_dlpack.register_lazy("tensorflow")
def _register_to_dlpack_from_tf():
    import tensorflow as tf

    eager_tensor_type = type(tf.random.uniform((1,)))

    @_to_dlpack.register(tf.Tensor)
    @_to_dlpack.register(eager_tensor_type)
    def _to_dlpack_from_tf_tensor(tensor):
        capsule = tf.experimental.dlpack.to_dlpack(tensor)

        dlpack_device = DlpackDevice.CUDA if "GPU" in tensor.device else DlpackDevice.CPU
        device_number = int(tensor.device.split(":")[-1])
        device = (dlpack_device, device_number)

        return TensorflowDlpackWrapper(capsule, device)


@_from_dlpack_cpu.register_lazy("tensorflow")
def _register_from_dlpack_cpu_to_tf():
    import tensorflow as tf

    eager_tensor_type = type(tf.random.uniform((1,)))

    @_from_dlpack_cpu.register(tf.Tensor)
    @_from_dlpack_cpu.register(eager_tensor_type)
    def _from_dlpack_cpu_to_tf(target_type, array):
        return tf.experimental.dlpack.from_dlpack(array.__dlpack__())


@_from_dlpack_gpu.register_lazy("tensorflow")
def _register_from_dlpack_gpu_to_tf():
    import tensorflow as tf

    eager_tensor_type = type(tf.random.uniform((1,)))

    @_from_dlpack_gpu.register(tf.Tensor)
    @_from_dlpack_gpu.register(eager_tensor_type)
    def _from_dlpack_gpu_to_tf(target_type, array):
        return tf.experimental.dlpack.from_dlpack(array.__dlpack__())
