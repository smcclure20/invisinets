import attrs
from typing import Callable
import transactions.context
from functools import wraps, partial


@attrs.define(slots=True)
class Action:
    undo: Callable
    f: Callable

    @classmethod
    def register(cls, undo_callback: Callable):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                action = cls(
                    undo=undo_callback,
                    f=partial(f, *args, **kwargs)
                )
                return transactions.context.current.add_action(action)

            return wrapper


@attrs.define(slots=True, init=False)
class ResourceAction(Action):

    def __init__(self, f: Callable):
        self.f = f
        self.undo = lambda r: r.terminate()

    @classmethod
    def register(cls, **kwargs):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                action = cls(
                    f=partial(f, *args, **kwargs)
                )
                return transactions.context.current.add_action(action)

            return wrapper
