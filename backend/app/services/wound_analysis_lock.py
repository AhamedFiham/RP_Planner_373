"""Cross-process run locks, released by the OS if an inference process exits."""

import os
from app.database.repositories import wound_repository as repository

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class RunLock:
    def __init__(self, run_id):
        directory = repository.data_directory() / "wound_analysis_locks"
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / (run_id + ".lock")
        if not self.path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Invalid analysis run identifier")
        self.file = self.path.open("a+b")
        self.acquired = False
        if self.file.seek(0, 2) == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.acquired = True
        except OSError:
            self.file.close()

    def close(self):
        if not self.acquired:
            return
        try:
            self.file.seek(0)
            if os.name == "nt":
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        finally:
            self.file.close()
            self.acquired = False
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                # Another recovery check may briefly hold this lock file open.
                pass

    def __enter__(self):
        if not self.acquired:
            raise RuntimeError("Analysis run lock is already held")
        return self

    def __exit__(self, *_):
        self.close()
