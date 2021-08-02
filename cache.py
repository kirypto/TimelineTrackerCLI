from datetime import datetime, timedelta
from time import sleep
from typing import Any, TypeVar, Optional, Callable, Dict

_MILLIS_PER_HOUR = 1000 * 60 * 60

TArg1 = TypeVar("TArg1")
TArg2 = TypeVar("TArg2")
TArg3 = TypeVar("TArg3")
TReturn = TypeVar("TReturn")


class Cache:
    _name: str
    _file: bool
    _timeout_ms: float
    _memory_cache: Dict[int, Any]
    _expirations: Dict[int, datetime]

    def __init__(self, name: str, *, file: bool = False, timeout_ms: float = _MILLIS_PER_HOUR) -> None:
        if file:
            raise NotImplementedError("File caching is not yet supported")
        self._name = name
        self._file = file
        self._timeout_ms = timeout_ms
        self._memory_cache = {}
        self._expirations = {}

    def get(self, method: Callable[[TArg1], TReturn], arg1: TArg1) -> Optional[TReturn]:
        return self._inner_get(method, arg1)

    def get2(self, method: Callable[[TArg1, TArg2], TReturn], arg1: TArg1, arg2: TArg2) -> Optional[TReturn]:
        return self._inner_get(method, arg1, arg2)

    def get3(self, method: Callable[[TArg1, TArg2, TArg3], TReturn], arg1: TArg1, arg2: TArg2, arg3: TArg3) -> Optional[TReturn]:
        return self._inner_get(method, arg1, arg2, arg3)

    def _inner_get(self, method: Callable[[Any], Any], *args: Any) -> Any:
        self._check_invalidations()
        item_hash = hash((method, *args))

        if item_hash not in self._memory_cache:
            self._store(item_hash, method(*args))

        return self._memory_cache[item_hash]

    def _check_invalidations(self) -> None:
        now = datetime.now()
        for item_hash, expiration_time in list(self._expirations.items()):
            if expiration_time < now:
                self._expirations.pop(item_hash)
                self._memory_cache.pop(item_hash)

    def _store(self, item_hash: int, item: Any) -> None:
        self._memory_cache[item_hash] = item
        self._expirations[item_hash] = datetime.now() + timedelta(milliseconds=self._timeout_ms)


def _test():
    print("running tests for Cache")
    test_data = {
        "test_successes": 0,
        "test_failures": 0,
        "foo_call_count": 0,
    }

    def ensure(message: str, expected: Any, actual: Any) -> None:
        test_output = f"Testing '{message}'; wanted: {expected}, got: {actual}"
        if expected == actual:
            test_data["test_successes"] += 1
            print(f"~~>  SUCCESS  {test_output}")
        else:
            test_data["test_failures"] += 1
            print(f"~~>  FAILURE  {test_output}")

    def foo(var1: str, var2: int) -> int:
        test_data["foo_call_count"] += 1
        return int(var1) + var2

    cache = Cache("test", file=False, timeout_ms=50)
    result = cache.get2(foo, "10", 5)
    ensure("Check cache get result on miss", 15, result)
    ensure("Check method passed to cache actually called on miss", 1, test_data["foo_call_count"])

    result = cache.get2(foo, "10", 5)
    ensure("Check cache get result on hit", 15, result)
    ensure("Check method passed to cache not called on hit", 1, test_data["foo_call_count"])

    sleep(0.1)
    result = cache.get2(foo, "10", 5)
    ensure("Check cache get result on miss due to expiry", 15, result)
    ensure("Check method passed to cache actually called on miss due to expiry", 2, test_data["foo_call_count"])

    success_count = test_data["test_successes"]
    failure_count = test_data["test_failures"]
    success_percent = (str(round(success_count / (success_count + failure_count) * 100)) + "%").ljust(4)
    print(f"~~>  RESULTS  {success_percent}     succeeded={success_count}, failed={failure_count}")


if __name__ == '__main__':
    _test()
