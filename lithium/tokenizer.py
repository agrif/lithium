import pyparsing as pyp
import codecs

class Expr:
    def __init__(self, s, loc, toks):
        self.col = pyp.col(loc, s)
        self.lineno = pyp.lineno(loc, s)
        self.line = pyp.line(loc, s)
        self.value = self._fromtoken(toks[0])
    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.value)
    def _fromtoken(self, tok):
        return tok

class List(Expr):
    def _fromtoken(self, tok):
        return tok.asList()

class String(Expr):
    def _fromtoken(self, tok):
        s = tok[1:-1]
        return codecs.getdecoder("unicode_escape")(s)[0]

class Symbol(Expr):
    pass

class Integer(Expr):
    def _token(self, tok):
        return int(tok)

LPAR, RPAR = map(pyp.Suppress, "()")

integer = pyp.Regex(r'-?0|[1-9]\d*').setParseAction(Integer)
symbol = pyp.Word(pyp.alphanums + "-./_:*+=").setParseAction(Symbol)
string = pyp.quotedString.setParseAction(String)
atom = integer | symbol | string

sexp = pyp.Forward()
sexpList = pyp.Group(LPAR + pyp.ZeroOrMore(sexp) + RPAR).setParseAction(List)
sexp << (atom | sexpList)

exprlist = pyp.ZeroOrMore(sexp)

def tokenize(f):
    return exprlist.parseFile(f, parseAll=False).asList()

if __name__ == "__main__":
    import sys
    for tok in tokenize(sys.stdin):
        print(tok)
