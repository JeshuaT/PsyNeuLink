#!/usr/bin/python3

import copy
import functools
import numpy as np
import pytest

from psyneulink.core import llvm as pnlvm
from llvmlite import ir


DIM_X=1000
TST_MIN=1.0
TST_MAX=3.0

vector = np.random.rand(DIM_X)

@pytest.mark.llvm
def test_helper_fclamp():

    with pnlvm.LLVMBuilderContext() as ctx:
        local_vec = copy.deepcopy(vector)
        double_ptr_ty = ctx.float_ty.as_pointer()
        func_ty = ir.FunctionType(ir.VoidType(), (double_ptr_ty, ctx.int32_ty))

        # Create clamp function
        custom_name = ctx.get_unique_name("clamp")
        function = ir.Function(ctx.module, func_ty, name=custom_name)
        vec, count = function.args
        block = function.append_basic_block(name="entry")
        builder = ir.IRBuilder(block)

        index = None
        with pnlvm.helpers.for_loop_zero_inc(builder, count, "linear") as (builder, index):
            val_ptr = builder.gep(vec, [index])
            val = builder.load(val_ptr)
            val = pnlvm.helpers.fclamp(builder, val, ctx.float_ty(TST_MIN), ctx.float_ty(TST_MAX))
            builder.store(val, val_ptr)

        builder.ret_void()

    ref = np.clip(vector, TST_MIN, TST_MAX)
    bin_f = pnlvm.LLVMBinaryFunction.get(custom_name)
    ct_ty = pnlvm._convert_llvm_ir_to_ctype(double_ptr_ty)
    ct_vec = local_vec.ctypes.data_as(ct_ty)

    bin_f(ct_vec, DIM_X)

    assert np.array_equal(local_vec, ref)


@pytest.mark.llvm
def test_helper_fclamp_const():

    with pnlvm.LLVMBuilderContext() as ctx:
        local_vec = copy.deepcopy(vector)
        double_ptr_ty = ctx.float_ty.as_pointer()
        func_ty = ir.FunctionType(ir.VoidType(), (double_ptr_ty, ctx.int32_ty))

        # Create clamp function
        custom_name = ctx.get_unique_name("clamp")
        function = ir.Function(ctx.module, func_ty, name=custom_name)
        vec, count = function.args
        block = function.append_basic_block(name="entry")
        builder = ir.IRBuilder(block)

        index = None
        with pnlvm.helpers.for_loop_zero_inc(builder, count, "linear") as (builder, index):
            val_ptr = builder.gep(vec, [index])
            val = builder.load(val_ptr)
            val = pnlvm.helpers.fclamp(builder, val, TST_MIN, TST_MAX)
            builder.store(val, val_ptr)

        builder.ret_void()

    ref = np.clip(vector, TST_MIN, TST_MAX)
    bin_f = pnlvm.LLVMBinaryFunction.get(custom_name)
    ct_ty = pnlvm._convert_llvm_ir_to_ctype(double_ptr_ty)
    ct_vec = local_vec.ctypes.data_as(ct_ty)

    bin_f(ct_vec, DIM_X)

    assert np.array_equal(local_vec, ref)
