from .parser import Defun, Call, Variable, IntConstant
from .types import ConstructedType, AtomicType, typify
from .generic import generic
from llvm import LLVMException
import llvm.core as llvm

class ScopeItem:
    def __init__(self, type, code):
        self.type = type
        self.code = code

class Builtin:
    pass

class Add(Builtin):
    type = ConstructedType('fn', AtomicType('int'), AtomicType('int'), AtomicType('int'))

    def call(self, args, fn, builder):
        a, b = args
        return builder.add(a, b)

builtins = {
    '+': Add()
}

@generic
def llvm_type(t):
    pass

@llvm_type.implementation(AtomicType)
def lt_AtomicType(t):
    if t.typename == 'int':
        return llvm.Type.int()
    else:
        raise RuntimeError("found unknown atomic type {}".format(t.typename))

@llvm_type.implementation(ConstructedType)
def lt_ConstructedType(t):
    if t.constructor == "fn":
        ret, *args = t.args
        return llvm.Type.function(llvm_type(ret), [llvm_type(ty) for ty in args])
    else:
        raise RuntimeError("found unknown constructed type {}".format(t.constructor))

@generic
def compile_expression(expr, fn, builder, scope, types):
    pass

@compile_expression.implementation(IntConstant)
def ce_IntConstant(expr, fn, builder, scope, types):
    ty = types.get(expr.type, expr.type)
    return llvm.Constant.int(llvm_type(ty), expr.info)

@compile_expression.implementation(Variable)
def ce_Variable(expr, fn, builder, scope, types):
    v = scope[expr.info]
    if isinstance(v, Builtin):
        return v
    return v.code

@compile_expression.implementation(Call)
def ce_Call(expr, fn, builder, scope, types):
    func = compile_expression(expr.info['function'], fn, builder, scope, types)
    args = [compile_expression(a, fn, builder, scope, types) for a in expr.info['tail']]
    if isinstance(func, Builtin):
        return func.call(args, fn, builder)
    else:
        return builder.call(func, args)

@generic
def compile_statement(stat, mod, scope):
    pass

@compile_statement.implementation(Defun)
def cs_Defun(stat, mod, scope):
    typerscope = {}
    subscope = scope.copy()
    for k, v in scope.items():
        typerscope[k] = v.type
    types = typify(stat, typerscope)

    ty = types.get(stat.type, stat.type)
    
    lty = llvm_type(ty)
    name = stat.info['name']
    fn = mod.add_function(lty, name)
    argtypes = ty.args[1:]
    for i, (argname, argtype) in enumerate(zip(stat.info['arguments'], argtypes)):
        fn.args[i].name = argname
        subscope[argname] = ScopeItem(argtype, fn.args[i])

    bb = fn.append_basic_block("entry")
    builder = llvm.Builder.new(bb)
    v = compile_expression(stat.info['tail'][-1], fn, builder, subscope, types)
    builder.ret(v)

    scope[name] = ScopeItem(ty, fn)

if __name__ == '__main__':
    import sys
    from .parser import parse_statement
    from .tokenizer import tokenize

    scope = builtins.copy()
    mod = llvm.Module.new('test')
    for tok in tokenize(sys.stdin):
        ast = parse_statement(tok)
        compile_statement(ast, mod, scope)
    print(mod)
