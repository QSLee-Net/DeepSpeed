# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: Apache-2.0

# DeepSpeed Team

import pytest
import torch
import deepspeed
from deepspeed.accelerator import get_accelerator
from deepspeed.ops.op_builder import InferenceBuilder
from deepspeed.ops.transformer import DeepSpeedInferenceConfig
from deepspeed.ops.transformer.inference.op_binding.bias_gelu import BiasGeluOp
from deepspeed.utils.torch import required_torch_version
from .inference_test_utils import allclose, get_dtypes

if not deepspeed.ops.__compatible_ops__[InferenceBuilder.NAME]:
    pytest.skip("Inference ops are not available on this system", allow_module_level=True)


def run_bias_gelu_reference(activations, bias):
    # Expected behavior is that of casting to float32 internally and using the tanh approximation
    return torch.nn.functional.gelu(activations.to(torch.float32) + bias.to(torch.float32),
                                    approximate='tanh').to(activations.dtype)


def run_bias_gelu_ds(activations, bias):
    config = DeepSpeedInferenceConfig(dtype=activations.dtype)
    return BiasGeluOp(config)(activations, bias)


@pytest.mark.inference_ops
@pytest.mark.parametrize("batch", [1, 2])
@pytest.mark.parametrize("sequence", [1, 128, 255])
@pytest.mark.parametrize("channels", [512, 1232, 4096])
@pytest.mark.parametrize("dtype", get_dtypes())
def test_bias_gelu(batch, sequence, channels, dtype):
    if not required_torch_version(min_version=1.12):
        pytest.skip("gelu implementation matches only after torch 1.12")

    activations_ds = torch.randn((batch, sequence, channels), dtype=dtype, device=get_accelerator().device_name())
    bias_ds = torch.randn((channels), dtype=dtype, device=get_accelerator().device_name())

    activations_ref = activations_ds.clone().detach()
    bias_ref = bias_ds.clone().detach()

    ds_out = run_bias_gelu_ds(activations_ds, bias_ds)
    ref_out = run_bias_gelu_reference(activations_ref, bias_ref)
    assert (allclose(ds_out, ref_out))
