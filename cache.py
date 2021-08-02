from datetime import datetime, timedelta
from pathlib import Path
from re import match
from time import sleep
from typing import Any, TypeVar, Optional, Callable, Dict
import pickle

_MILLIS_PER_HOUR = 1000 * 60 * 60

TArg1 = TypeVar("TArg1")
TArg2 = TypeVar("TArg2")
TArg3 = TypeVar("TArg3")
TReturn = TypeVar("TReturn")


class Cache:
    _name: str
    _file_path: Optional[Path]
    _timeout_ms: float
    _memory_cache: Dict[int, Any]
    _expirations: Dict[int, datetime]

    def __init__(self, name: str, *, file: bool = False, timeout_ms: float = _MILLIS_PER_HOUR) -> None:
        if not match(r"^[a-zA-Z0-9]+$", name):
            raise ValueError("Argument 'name' must only have alpha-numeric characters")
        self._name = name
        self._file_path = Path(__file__).parent.joinpath(f"__local_cache__/__{name}__") if file else None
        self._timeout_ms = timeout_ms
        self._memory_cache = {}
        self._expirations = {}

    def get(self, method: Callable[[TArg1], TReturn], arg1: TArg1) -> Optional[TReturn]:
        return self._inner_get(method, arg1)

    def get2(self, method: Callable[[TArg1, TArg2], TReturn], arg1: TArg1, arg2: TArg2) -> Optional[TReturn]:
        return self._inner_get(method, arg1, arg2)

    def get3(self, method: Callable[[TArg1, TArg2, TArg3], TReturn], arg1: TArg1, arg2: TArg2, arg3: TArg3) -> Optional[TReturn]:
        return self._inner_get(method, arg1, arg2, arg3)

    def flush(self) -> None:
        self._memory_cache = {}
        self._expirations = {}

    def _inner_get(self, method: Callable[[Any], Any], *args: Any) -> Any:
        self._check_memory_invalidations()
        item_hash = hash((method, *args))

        if item_hash not in self._memory_cache:
            self._update_from_file_cache()

        if item_hash not in self._memory_cache:
            self._store(item_hash, method(*args))

        return self._memory_cache[item_hash]

    def _check_memory_invalidations(self) -> None:
        now = datetime.now()
        for item_hash, expiration_time in list(self._expirations.items()):
            if expiration_time < now:
                self._expirations.pop(item_hash)
                self._memory_cache.pop(item_hash)

    def _store(self, item_hash: int, item: Any) -> None:
        self._update_from_file_cache()
        self._memory_cache[item_hash] = item
        self._expirations[item_hash] = datetime.now() + timedelta(milliseconds=self._timeout_ms)
        self._write_to_file_cache()

    def _update_from_file_cache(self) -> None:
        if self._file_path is None:
            return
        now = datetime.now()
        with open(self._file_path, "rb") as cache_file:
            cache_contents = pickle.load(cache_file)
            cache_items: Dict[int, Any] = cache_contents["items"]
            cache_expirations: Dict[int, datetime] = cache_contents["expirations"]
            for item_hash, expiration_time in cache_expirations.items():
                time_now = expiration_time > now
                if time_now and (item_hash not in self._expirations or expiration_time > self._expirations[item_hash]):
                    self._expirations[item_hash] = expiration_time
                    self._memory_cache[item_hash] = cache_items[item_hash]

    def _write_to_file_cache(self) -> None:
        if self._file_path is None:
            return
        with open(self._file_path.as_posix(), "wb") as cache_file:
            cache_contents = {
                "items": self._memory_cache,
                "expirations": self._expirations,
            }
            pickle.dump(cache_contents, cache_file, protocol=pickle.HIGHEST_PROTOCOL)


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
    ensure("Check method actually called on miss", 1, test_data["foo_call_count"])

    result = cache.get2(foo, "10", 5)
    ensure("Check cache get result on hit", 15, result)
    ensure("Check method not called on hit", 1, test_data["foo_call_count"])

    sleep(0.1)
    result = cache.get2(foo, "10", 5)
    ensure("Check cache get result on miss due to expiry", 15, result)
    ensure("Check method actually called on miss due to expiry", 2, test_data["foo_call_count"])

    cache.flush()
    result = cache.get2(foo, "10", 5)
    ensure("Check cache get result on miss due to flush", 15, result)
    ensure("Check method actually called on miss due to flush", 3, test_data["foo_call_count"])

    result = cache.get2(foo, "4", 8)
    ensure("Check cache get result on miss due to differing args", 12, result)
    ensure("Check method actually called on miss due to differing args", 4, test_data["foo_call_count"])

    file_cache1 = Cache("test", file=True, timeout_ms=50)
    file_cache2 = Cache("test", file=True, timeout_ms=50)
    test_data["foo_call_count"] = 0
    result = file_cache1.get2(foo, "20", 13)
    ensure("Check file cache get result on miss", 33, result)
    ensure("Check method actually called on miss", 1, test_data["foo_call_count"])

    result = file_cache2.get2(foo, "20", 13)
    ensure("Check file cache get result on file hit", 33, result)
    ensure("Check method not called on file hit", 1, test_data["foo_call_count"])

    result = file_cache1.get2(foo, "25", 15)
    ensure("Check file cache get result on miss", 40, result)
    ensure("Check method actually called on miss", 2, test_data["foo_call_count"])

    sleep(0.1)
    result = file_cache2.get2(foo, "25", 15)
    ensure("Check file cache get result on file miss due to expiry", 40, result)
    ensure("Check method not called on file miss due to expiry", 3, test_data["foo_call_count"])

    success_count = test_data["test_successes"]
    failure_count = test_data["test_failures"]
    success_percent = (str(round(success_count / (success_count + failure_count) * 100)) + "%").ljust(4)
    print(f"~~>  RESULTS  {success_percent}     succeeded={success_count}, failed={failure_count}")


if __name__ == '__main__':
    _test()
