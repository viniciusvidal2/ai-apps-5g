# Copyright (c) Meta Platforms, Inc. and affiliates. All Rights Reserved

# pyre-unsafe

import torch
import torch.nn.functional as F

addmm_act_op = torch.ops.aten._addmm_activation


def addmm_act(activation, linear, mat1):
    if torch.is_grad_enabled():
        raise ValueError("Expected grad to be disabled.")
    bias = linear.bias.detach() if linear.bias is not None else None
    weight = linear.weight.detach()
    target_dtype = weight.dtype
    mat1 = mat1.to(target_dtype)

    # Caminho seguro: mantem o dtype consistente com os pesos do modulo.
    # Isso evita conflitos bf16/float32 em ambientes onde a lib fused promove
    # parcialmente os tensores.
    if target_dtype not in (torch.bfloat16, torch.float16) or not mat1.is_cuda:
        y = F.linear(mat1, weight, bias)
        if activation in [torch.nn.functional.relu, torch.nn.ReLU]:
            return F.relu(y)
        if activation in [torch.nn.functional.gelu, torch.nn.GELU]:
            return F.gelu(y)
        raise ValueError(f"Unexpected activation {activation}")

    self = bias
    mat2 = weight
    self = self.to(target_dtype) if self is not None else torch.zeros(
        mat2.shape[0], device=mat1.device, dtype=target_dtype
    )
    mat2 = mat2.to(target_dtype)
    mat1_flat = mat1.view(-1, mat1.shape[-1])
    if activation in [torch.nn.functional.relu, torch.nn.ReLU]:
        y = addmm_act_op(self, mat1_flat, mat2.t(), beta=1, alpha=1, use_gelu=False)
        return y.view(mat1.shape[:-1] + (y.shape[-1],))
    if activation in [torch.nn.functional.gelu, torch.nn.GELU]:
        y = addmm_act_op(self, mat1_flat, mat2.t(), beta=1, alpha=1, use_gelu=True)
        return y.view(mat1.shape[:-1] + (y.shape[-1],))
    raise ValueError(f"Unexpected activation {activation}")
