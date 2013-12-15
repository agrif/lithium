from functools import wraps

# calls fn first, then the implementation
def generic(fn):
    table = []
    @wraps(fn)
    def dispatcher(obj, *args, **kwargs):
        nonlocal table
        for klass, f in table:
            if isinstance(obj, klass):
                fn(obj, *args, **kwargs)
                return f(obj, *args, **kwargs)
        raise ValueError("no implementation of {} for {}".format(fn.__name__, obj.__class__.__name__))

    def implementation(klass):
        def subimpl(impl):
            nonlocal table
            table.append((klass, impl))
            return impl
        return subimpl
    dispatcher.implementation = implementation

    return dispatcher
