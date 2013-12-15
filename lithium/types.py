from .parser import Variable, IntConstant, Call, Defun
from .generic import generic
import string
import copy

class TypingError(Exception):
    def __init__(self, expr, s):
        self.expr = expr
        super(TypingError, self).__init__(s)

    def __str__(self):
        return "{} at line {} col {}".format(self.args[0], self.expr.tok.lineno, self.expr.tok.col)

class Type:
    def substitute(self, x, y):
        # return a type where x -> y
        # x is *always* an indefinite type
        raise NotImplementedError("{}.substitute".format(self.__class__.__name__))
    def instantiate(self):
        # get rid of any quantified typevariables
        # replace them with a new typevariable
        raise NotImplementedError("{}.instantiate".format(self.__class__.__name__))
    def free_typevars(self):
        # iterate over contained indefinite types, yield only free
        raise NotImplementedError("{}.free_typevars".format(self.__class__.__name__))
    def __ne__(self, other):
        return not (self == other)

class IndefiniteType(Type):
    nexti = 0
    def __init__(self):
        self.assumptions = {}
        i = self.__class__.nexti
        self.__class__.nexti += 1
        append = i // len(string.ascii_uppercase)
        i = i % len(string.ascii_uppercase)
        base = string.ascii_uppercase[i]
        if append > 0:
            base = "{}{}".format(base, append)
        self.typename = base
    def substitute(self, x, y):
        if self == x:
            return y
        return self
    def instantiate(self):
        return self
    def free_typevars(self):
        yield self
    def __repr__(self):
        return "{}".format(self.typename)
    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.typename == other.typename
    def __hash__(self):
        return hash(self.typename)

class AtomicType(Type):
    def __init__(self, typename):
        self.assumptions = {}
        self.typename = typename
    def substitute(self, x, y):
        return self
    def instantiate(self):
        return self
    def free_typevars(self):
        if False:
            yield
    def __repr__(self):
        return self.typename
    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.typename == other.typename

class ConstructedType(Type):
    def __init__(self, constructor, *args):
        self.assumptions = {}
        self.constructor = constructor
        self.args = args
    def substitute(self, x, y):
        args = [T.substitute(x, y) for T in self.args]
        return ConstructedType(self.constructor, *args)
    def instantiate(self):
        args = [T.instantiate() for T in self.args]
        return ConstructedType(self.constructor, *args)
    def free_typevars(self):
        for T in self.args:
            for S in T.free_typevars():
                yield S
    def __repr__(self):
        if self.constructor == 'fn':
            return "{} -> {}".format(repr(self.args[1:]), self.args[0])
        return "{}{}".format(self.constructor, repr(self.args))
    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.constructor == other.constructor and self.args == other.args

class QuantifiedType(Type):
    def __init__(self, variable, result):
        self.assumptions = {}
        self.variable = variable
        self.result = result
    def instantiate(self, withvar=None):
        if withvar is None:
            withvar = IndefiniteType()
        return self.result.substitute(self.variable, withvar)
    def substitute(self, x, y):
        assert x != self.variable
        return QuantifiedType(self.variable, self.result.substitute(x, y))
    def free_typevars(self):
        for T in self.result.free_typevars():
            if T != self.variable:
                yield T
    def __repr__(self):
        return "forall {}. {}".format(self.variable, self.result)
    def __eq__(self, other):
        if type(other) != type(self):
            return False
        var = IndefiniteType()
        return self.instantiate(var) == other.instantiate(var)

def forall(fn):
    var = IndefiniteType()
    result = fn(var)
    return QuantifiedType(var, result)

@generic
def generate_typerules(expr, exprtype, scope):
    # assumptions only updated here and in the lambda form
    # in the lambda form because that's the only place generate_typerules
    # isn't called on some types
    exprtype.assumptions.update(scope)
    expr.type = exprtype

@generate_typerules.implementation(Variable)
def gt_Variable(expr, exprtype, scope):
    try:
        return [(exprtype, scope[expr.info])]
    except KeyError as e:
        raise TypingError(expr, "variable not in scope: {}".format(expr.info)) from e

@generate_typerules.implementation(IntConstant)
def gt_IntConstant(expr, exprtype, scope):
    return [(exprtype, AtomicType('int'))]

@generate_typerules.implementation(Call)
def gt_Call(expr, exprtype, scope):
    name = expr.info['function']
    args = expr.info['tail']
    rules = []

    nametype = IndefiniteType()
    rules += generate_typerules(name, nametype, scope)
    argtypes = []
    for arg in args:
        argtype = IndefiniteType()
        rules += generate_typerules(arg, argtype, scope)
        argtypes.append(argtype)
    rules.append((nametype, ConstructedType('fn', exprtype, *argtypes)))
    return rules

@generate_typerules.implementation(Defun)
def gt_Defun(expr, exprtype, scope):
    args = expr.info['arguments']
    body = expr.info['tail'][-1]

    argtypes = []
    subscope = scope.copy()
    for name in args:
        nametype = IndefiniteType()
        # not needed for new IndefiniteType, but needed if some argument
        # is explicitly named as an earlier indefinite type
        nametype.assumptions.update(scope)
        argtypes.append(nametype)
        subscope[name] = nametype
    bodytype = IndefiniteType()

    fntype = ConstructedType('fn', bodytype, *argtypes)
    rules = [(exprtype, fntype)] + generate_typerules(body, bodytype, subscope)
    return rules
    
def unify(rules):    
    subst = {}
    stack = copy.copy(rules)

    def add_subst(x, y):
        nonlocal stack, subst
        fy = lambda: y.instantiate()
        stack = [(A.substitute(x, fy()), B.substitute(x, fy())) for (A, B) in stack]
        newsubst = {}
        for K, V in subst.items():
            # we should never change a key
            assert K.substitute(x, fy()) == K
            assumptions = {}
            for name, assump in K.assumptions.items():
                assumptions[name] = assump.substitute(x, fy())
            K.assumptions = assumptions
            newsubst[K] = V.substitute(x, fy())
        subst = newsubst
        subst[x] = y

    while stack:
        X, Y = stack.pop(0)
        if X == Y:
            pass
        elif type(X) == IndefiniteType:
            add_subst(X, Y)
        elif type(Y) == IndefiniteType:
            add_subst(Y, X)
        else:
            X = X.instantiate()
            Y = Y.instantiate()
            if X == Y:
                pass
            elif type(X) == IndefiniteType:
                add_subst(X, Y)
            elif type(Y) == IndefiniteType:
                add_subst(Y, X)
            elif type(X) == ConstructedType and type(Y) == ConstructedType and \
                X.constructor == Y.constructor and len(X.args) == len(Y.args):
                for (Xa, Ya) in zip(X.args, Y.args):
                    stack.append((Xa, Ya))
            else:
                raise RuntimeError("could not unify: {} and {}".format(X, Y))

    def is_free(T, assumptions):
        for V in assumptions.values():
            if T in V.free_typevars():
                return True
        return False
    
    quantsubst = {}
    for K, V in subst.items():
        for T in set(V.free_typevars()):
            if not is_free(T, K.assumptions):
                V = QuantifiedType(T, V)
        quantsubst[K] = V
    return quantsubst

def typify(expr, scope):
    t = IndefiniteType()
    rules = generate_typerules(expr, t, scope)
    subst = unify(rules)
    return subst

if __name__ == "__main__":
    examplescope = {
        'x': IndefiniteType(),
        '+': ConstructedType('fn', AtomicType('int'), AtomicType('int'), AtomicType('int')),
    }
    import sys
    from .parser import parse_statement, parse_expression
    from .tokenizer import tokenize
    for tok in tokenize(sys.stdin):
        ast = parse_statement(tok)
        print(typify(ast, examplescope))
