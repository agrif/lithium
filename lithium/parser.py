from .tokenizer import Integer
from .patterns import *

class ParseError(Exception):
    def __init__(self, tok, s):
        self.tok = tok
        super(ParseError, self).__init__(s)

    def __str__(self):
        return "{} at line {} col {}".format(self.args[0], self.tok.lineno, self.tok.col)

class Parser:
    loosepattern = None
    pattern = None
    def __init__(self, tok, info):
        self.tok = tok
        self.info = info
    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.info)

statements = []
expressions = []
def statement(klass):
    global statements
    statements.append(klass)
    return klass
def expression(klass):
    global expressions
    expressions.append(klass)
    return klass

def parse_from(tok, parsers):
    for p in parsers:
        try:
            loosepattern = p.loosepattern
            if loosepattern is None:
                loosepattern = p.pattern
            loosepattern.matchq(tok)
        except PatternMatchError:
            continue
        
        try:
            info = p.pattern.match(tok)
            return p(tok, info)
        except PatternMatchError as e:
            raise ParseError(e.tok, *e.args) from e
    raise ParseError(tok, "unknown form")

def parse_expression(tok):
    return parse_from(tok, expressions)

def parse_statement(tok):
    return parse_from(tok, statements)

@statement
class Defun(Parser):
    loosepattern = PForm(PKeyword("defun"), tail=PAny())
    pattern = PForm(PKeyword("defun"), PSymbol(name='name'), PListOf(PSymbol(), name='arguments'), tail=PAny())
    
    def __init__(self, tok, info):
        super(Defun, self).__init__(tok, info)
        self.info['tail'] = [parse_expression(t) for t in self.info['tail']]

@expression
class Call(Parser):
    pattern = PForm(PAny(name="function"), tail=PAny())

    def __init__(self, tok, info):
        super(Call, self).__init__(tok, info)
        self.info['function'] = parse_expression(self.info['function'])
        self.info['tail'] = [parse_expression(t) for t in self.info['tail']]

@expression
class IntConstant(Parser):
    pattern = PClass(Integer)

@expression
class Variable(Parser):
    pattern = PSymbol()

if __name__ == "__main__":
    import sys
    from .tokenizer import tokenize
    for tok in tokenize(sys.stdin):
        ast = parse_statement(tok)
        print(ast)
