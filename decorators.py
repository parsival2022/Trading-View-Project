import time, random
from typing import Callable, Type, Union, Tuple, Any

def repeat_if_fail(exceptions:Union[Type[Exception], list[Type[Exception]]], wait:Union[int, Tuple[int, int]] = None) -> Any:
    def decorator(func:Callable):
        def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if wait: 
                        try:
                             t = random.randint(wait)
                        except TypeError:
                             t = wait
                        time.sleep(t)
                    return func(*args, **kwargs)
        return wrapper
    return decorator

def execute_if_fail(exception:Exception, exec:Callable) -> Any:
    def decorator(func:Callable):
        def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exception:
                    return exec()
        return wrapper
    return decorator

def ignore_if_fail(exception:Exception) -> Any:
    def decorator(func:Callable):
        def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exception:
                    pass
        return wrapper
    return decorator
