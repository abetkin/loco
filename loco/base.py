from contextlib import suppress
from functools import wraps

class Patch:

    def __init__(self, co, parent, attribute):
        self.co = co
        self.parent = parent
        self.attribute = attribute
        self.original = getattr(self.parent, self.attribute, None)
        self.wrapper = self.make_wrapper(self.original)

    def on(self):
        setattr(self.parent, self.attribute, self.wrapper)

    def off(self):
        if self.original:
            setattr(self.parent, self.attribute, self.original)
        else:
            delattr(self.parent, self.attribute)

    def __or__(self, other):
        return AnyCall(self, other)

    def make_wrapper(self, wrapped):
        wrapped = self.original
        __self__ = getattr(wrapped, '__self__', None)
        if __self__:
             wrapped = wrapped.__func__

        @wraps(wrapped)
        def func(*args, **kwargs):
            # import ipdb
            # with ipdb.launch_ipdb_on_exception():
            ret = wrapped(*args, **kwargs)
            call_args = CallArgs(func, args, kwargs)
            with suppress(StopIteration):
                self.co.send((ret, call_args))
            return ret

        if isinstance(__self__, type):
            func = classmethod(func)
        elif __self__:
            # FIXME add import
            func = MethodType(func, __self__)
        return func


class AnyCall(object):
    def __init__(self, *calls):
        self.calls = calls



import inspect

class CallArgs:

    def __init__(self, func, args, kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._signature = inspect.signature(func)
        self.bound_args = self._signature.bind(*args, **kwargs).arguments


    def __getitem__(self, key):
        if isinstance(key, int):
            return self.args[key]
        value = self.bound_args.get(key, NotImplemented)
        if value is not NotImplemented:
            return value
        value = self._signature.parameters.get(key, NotImplemented)
        if value is not NotImplemented:
            return value
        return KeyError(key)

    def __repr__(self):
        def pairs():
            for name, parameter in self._signature.parameters.items():
                value = self.bound_args.get(name, parameter.default)
                yield "%s=%s" % (name, value)
        return '(%s)' % ', '.join(pairs())

    def __iter__(self):
        return iter(self.args)




class Loco:
    # TODO: add unittest asserts

    def __init__(self, name):
        self.name = name
        func = getattr(self, name)
        self._gen_func = func
        self._gen = iter(self)

    def __call__(self, result):
        with suppress(StopIteration):
            p = self._gen.send(None)

    def call(self, container, attr):
        return Patch(self._gen, container, attr)

    def __iter__(self):
        co = self._gen_func()
        with suppress(StopIteration):
            val = None
            while True: #?
                value = co.send(val)
                if isinstance(value, AnyCall):
                    for i, p in enumerate(value.calls):
                        p.on()
                    val = (yield)
                    
                    # TODO check
                    # value.calls[1].original==val[1].func

                    ipdb.set_trace()
                    for p in value.calls:
                        p.off()
                    continue

                    


                p = value
                # container, attr = co.send(val)
                p.on()
                val = (yield)
                p.off()


