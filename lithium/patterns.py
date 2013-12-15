from .tokenizer import List, Symbol

class PatternMatchError(Exception):
    def __init__(self, tok, s):
        self.tok = tok
        super(PatternMatchError, self).__init__(s)

class Pattern:
    def __init__(self, name=None):
        self.name = name
    def convert(self, expr):
        # used in match to extract info
        return expr
    def match(self, expr):
        # return a match info object, or raise PatternMatchError
        self.matchq(expr)
        return self.convert(expr)
    def matchq(self, expr):
        # raise a PatternMatchError if we don't match
        raise NotImplementedError("{}.matchq".format(self.__class__.__name__))

class PAny(Pattern):
    def matchq(self, expr):
        pass

class PKeyword(Pattern):
    def __init__(self, keyword, name=None):
        self.keyword = keyword
        super(PKeyword, self).__init__(name)
    def convert(self, expr):
        return self.keyword
    def matchq(self, expr):
        if not isinstance(expr, Symbol) or expr.value != self.keyword:
            raise PatternMatchError(expr, "expected keyword {}".format(self.keyword))

class PClass(Pattern):
    def __init__(self, klass, name=None):
        self.klass = klass
        super(PClass, self).__init__(name)
    def convert(self, expr):
        return expr.value
    def matchq(self, expr):
        if not isinstance(expr, self.klass):
            raise PatternMatchError(expr, "expected {}".format(self.klass.__name__))

PSymbol = lambda *args, **kwargs: PClass(Symbol, *args, **kwargs)

class PListOf(Pattern):
    def __init__(self, subpat, name=None):
        self.subpat = subpat
        super(PListOf, self).__init__(name)
    def convert(self, expr):
        return [self.subpat.convert(subexpr) for subexpr in expr.value]
    def matchq(self, expr):
        if not isinstance(expr, List):
            raise PatternMatchError(expr, "expected list")
        for subexpr in expr.value:
            self.subpat.matchq(subexpr)

class PForm(Pattern):
    def __init__(self, *heads, tail=None, name=None):
        self.heads = heads
        self.tail = tail
        super(PForm, self).__init__(name)
    def _matched(self, l):
        if len(l) < len(self.heads):
            raise ValueError("mismatched lengths")
        if self.tail is None:
            if len(l) != len(self.heads):
                raise ValueError("mismatched lengths")
            return zip(self.heads, l)
        return zip(list(self.heads) + [self.tail] * (len(l) - len(self.heads)), l)
    def convert(self, expr):
        info = {}
        tail = []
        for i, (subpat, subexpr) in enumerate(self._matched(expr.value)):
            if subpat.name is None and i < len(self.heads):
                continue
            val = subpat.convert(subexpr)
            if subpat.name is not None:
                info[subpat.name] = val
            if i >= len(self.heads):
                tail.append(val)
        if self.tail is not None:
            info['tail'] = tail
        return info
    def matchq(self, expr):
        if not isinstance(expr, List):
            raise PatternMatchError(expr, "expected list")
        try:
            for subpat, subexpr in self._matched(expr.value):
                subpat.matchq(subexpr)
            return
        except ValueError:
            pass

        # we can only get here on ValueError
        if len(expr.value) > len(self.heads) and self.tail is None:
            raise PatternMatchError(expr, "unexpected stuff at end of list")
        if len(expr.value) < len(self.heads):
            # try to match what's there, at least
            for subpat, subexpr in zip(self.heads, expr.value):
                subpat.matchq(subexpr)
                
            # now complain about the missing last subpat
            subpat = self.heads[len(expr.value)]
            try:
                subpat.matchq(None)
            except PatternMatchError as e:
                e.tok = expr
                e.args = (e.args[0] + ' at end of list',)
                raise e
