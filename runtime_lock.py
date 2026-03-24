import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_LOCK_PATH = Path(__file__).resolve().parent / ".run" / "discord-bot.lock"


@contextmanager
def single_instance_lock() -> Iterator[None]:
    _LOCK_PATH.parent.mkdir(exist_ok=True)
    lock_file = _LOCK_PATH.open("a+")

    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            lock_file.seek(0)
            running_pid = lock_file.read().strip()
            if running_pid:
                raise RuntimeError(
                    f"Another bot instance is already running (PID {running_pid})."
                ) from exc
            raise RuntimeError("Another bot instance is already running.") from exc

        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()

        yield
    finally:
        try:
            lock_file.seek(0)
            lock_file.truncate()
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()
