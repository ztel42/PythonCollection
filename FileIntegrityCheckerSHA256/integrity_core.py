"""
Core SHA256 integrity helpers — hashing, compare, batch verify, live monitor.

No GUI imports so pytest can run headless.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Union

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:  # pragma: no cover - optional until installed
    FileSystemEventHandler = object  # type: ignore
    Observer = None  # type: ignore


CHUNK_SIZE = 65536


def sha256_bytes(data: bytes) -> str:
    """Return lowercase hex SHA256 of *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Union[str, Path], chunk_size: int = CHUNK_SIZE) -> str:
    """Stream a file and return its lowercase hex SHA256 digest."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def compare_hashes(a: str, b: str) -> bool:
    """Case-insensitive equality of two hex digests (whitespace stripped)."""
    return a.strip().lower() == b.strip().lower()


@dataclass
class BatchItemResult:
    path: str
    computed_hash: Optional[str]
    expected_hash: Optional[str]
    status: str  # MATCH | MISMATCH | HASHED | ERROR
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status in ("MATCH", "HASHED")


@dataclass
class BatchVerifyResult:
    results: List[BatchItemResult] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def match_count(self) -> int:
        return sum(1 for r in self.results if r.status == "MATCH")

    @property
    def mismatch_count(self) -> int:
        return sum(1 for r in self.results if r.status == "MISMATCH")

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status == "ERROR")

    def to_report_text(self) -> str:
        lines = [
            "--- Batch File Integrity Report ---",
            f"Date: {self.generated_at}",
            f"Files: {len(self.results)}",
            f"Matches: {self.match_count}  Mismatches: {self.mismatch_count}  Errors: {self.error_count}",
            "-" * 40,
        ]
        for r in self.results:
            lines.append(f"File: {r.path}")
            lines.append(f"  SHA256:   {r.computed_hash or 'n/a'}")
            if r.expected_hash:
                lines.append(f"  Expected: {r.expected_hash}")
            lines.append(f"  Status:   {r.status}" + (f" ({r.error})" if r.error else ""))
            lines.append("-" * 40)
        return "\n".join(lines) + "\n"


def parse_expected_hash_list(text: str) -> Dict[str, str]:
    """
    Parse an expected-hash list.

    Accepted lines:
      <sha256>  <filename-or-path>
      <filename-or-path>=<sha256>
      <filename-or-path>:<sha256>
    Blank lines and # comments are ignored. Keys are basename (lower) and full path (lower).
    """
    mapping: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key: Optional[str] = None
        value: Optional[str] = None
        if "=" in line and not line.split("=", 1)[0].strip().count(" "):
            left, right = line.split("=", 1)
            key, value = left.strip(), right.strip()
        elif ":" in line and len(line.split(":", 1)[0].strip()) < 80:
            left, right = line.split(":", 1)
            # hex digests contain only [0-9a-f] — if left looks like a hash, treat as "hash path"
            if len(left.strip()) == 64 and all(c in "0123456789abcdefABCDEF" for c in left.strip()):
                value, key = left.strip(), right.strip()
            else:
                key, value = left.strip(), right.strip()
        else:
            parts = line.split(None, 1)
            if len(parts) == 2:
                first, second = parts
                if len(first) == 64 and all(c in "0123456789abcdefABCDEF" for c in first):
                    value, key = first, second
                elif len(second) == 64 and all(c in "0123456789abcdefABCDEF" for c in second):
                    key, value = first, second
        if key and value:
            mapping[key.lower()] = value.strip().lower()
            mapping[Path(key).name.lower()] = value.strip().lower()
    return mapping


def lookup_expected(path: Union[str, Path], expected: Dict[str, str]) -> Optional[str]:
    path = Path(path)
    for candidate in (str(path).lower(), path.name.lower(), path.as_posix().lower()):
        if candidate in expected:
            return expected[candidate]
    return None


def batch_verify(
    paths: Sequence[Union[str, Path]],
    expected: Optional[Dict[str, str]] = None,
) -> BatchVerifyResult:
    """Hash each path; optionally compare to *expected* map (see parse_expected_hash_list)."""
    expected = expected or {}
    out = BatchVerifyResult()
    for p in paths:
        p = Path(p)
        exp = lookup_expected(p, expected) if expected else None
        try:
            computed = sha256_file(p)
            if exp is None:
                status = "HASHED"
            elif compare_hashes(computed, exp):
                status = "MATCH"
            else:
                status = "MISMATCH"
            out.results.append(
                BatchItemResult(
                    path=str(p),
                    computed_hash=computed,
                    expected_hash=exp,
                    status=status,
                )
            )
        except Exception as exc:  # noqa: BLE001 — surface per-file errors in batch
            out.results.append(
                BatchItemResult(
                    path=str(p),
                    computed_hash=None,
                    expected_hash=exp,
                    status="ERROR",
                    error=str(exc),
                )
            )
    return out


def format_single_report(
    file_path: str,
    sha256: str,
    status: str,
    when: Optional[datetime] = None,
) -> str:
    when = when or datetime.now()
    return (
        f"\n--- File Integrity Report ---\n"
        f"Date: {when.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"File: {file_path}\n"
        f"SHA256: {sha256}\n"
        f"Status: {status}\n"
        f"{'-' * 40}\n"
    )


# ---------------------------------------------------------------------------
# Live hash monitor (watchdog)
# ---------------------------------------------------------------------------

AlertCallback = Callable[[str, str, Optional[str], str], None]
# (path, current_hash, baseline_hash_or_None, message)


class _HashEventHandler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(
        self,
        monitor: "HashMonitor",
    ) -> None:
        super().__init__()
        self._monitor = monitor

    def on_modified(self, event):  # noqa: ANN001
        if getattr(event, "is_directory", False):
            return
        self._monitor._handle_path(event.src_path)

    def on_created(self, event):  # noqa: ANN001
        if getattr(event, "is_directory", False):
            return
        self._monitor._handle_path(event.src_path)

    def on_moved(self, event):  # noqa: ANN001
        if getattr(event, "is_directory", False):
            return
        dest = getattr(event, "dest_path", None)
        if dest:
            self._monitor._handle_path(dest)


class HashMonitor:
    """
    Watch files or a folder; recompute SHA256 on change and alert if it differs
    from the recorded baseline.

    *on_alert(path, current_hash, baseline_hash, message)* is invoked from the
    watchdog thread — callers that touch a GUI must marshal to the UI thread.
    """

    def __init__(
        self,
        on_alert: Optional[AlertCallback] = None,
        debounce_seconds: float = 0.35,
    ) -> None:
        if Observer is None:
            raise ImportError("watchdog is required for HashMonitor; pip install watchdog")
        self._on_alert = on_alert
        self._debounce = debounce_seconds
        self._baselines: Dict[str, str] = {}
        self._watched_files: set[str] = set()
        self._folder: Optional[str] = None
        self._observer: Optional[Observer] = None  # type: ignore[type-arg]
        self._lock = threading.Lock()
        self._last_fire: Dict[str, float] = {}
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def baselines(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._baselines)

    def set_baseline(self, path: Union[str, Path], digest: Optional[str] = None) -> str:
        """Record baseline hash for *path* (compute if *digest* omitted)."""
        path = str(Path(path).resolve())
        if digest is None:
            digest = sha256_file(path)
        with self._lock:
            self._baselines[path] = digest.lower()
            self._watched_files.add(path)
        return digest.lower()

    def clear_baselines(self) -> None:
        with self._lock:
            self._baselines.clear()
            self._watched_files.clear()

    def start(
        self,
        paths: Optional[Iterable[Union[str, Path]]] = None,
        folder: Optional[Union[str, Path]] = None,
        establish_baselines: bool = True,
    ) -> None:
        """Start watching *paths* and/or *folder*. Stops any previous observer."""
        self.stop()
        resolved_files: List[str] = []
        if paths:
            for p in paths:
                rp = str(Path(p).resolve())
                if not Path(rp).is_file():
                    raise FileNotFoundError(f"Not a file: {rp}")
                resolved_files.append(rp)
                if establish_baselines:
                    self.set_baseline(rp)

        watch_dirs: set[str] = set()
        if folder:
            folder_r = str(Path(folder).resolve())
            if not Path(folder_r).is_dir():
                raise NotADirectoryError(f"Not a directory: {folder_r}")
            self._folder = folder_r
            watch_dirs.add(folder_r)
            if establish_baselines:
                for child in Path(folder_r).iterdir():
                    if child.is_file():
                        self.set_baseline(child)
        else:
            self._folder = None

        for rp in resolved_files:
            watch_dirs.add(str(Path(rp).parent))

        if not watch_dirs:
            raise ValueError("Provide at least one file path or a folder to monitor.")

        handler = _HashEventHandler(self)
        observer = Observer()
        for d in watch_dirs:
            observer.schedule(handler, d, recursive=bool(folder))
        observer.daemon = True
        observer.start()
        self._observer = observer
        self._running = True

    def stop(self) -> None:
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception:  # noqa: BLE001
                pass
            self._observer = None
        self._running = False

    def check_path_now(self, path: Union[str, Path]) -> tuple[str, Optional[str], bool]:
        """
        Recompute hash for *path* and compare to baseline.

        Returns (current_hash, baseline_or_None, matches).
        If no baseline exists, records one and returns matches=True.
        """
        path = str(Path(path).resolve())
        current = sha256_file(path)
        with self._lock:
            baseline = self._baselines.get(path)
            if baseline is None:
                self._baselines[path] = current
                self._watched_files.add(path)
                return current, None, True
            return current, baseline, compare_hashes(current, baseline)

    def _relevant(self, path: str) -> bool:
        path = str(Path(path).resolve())
        with self._lock:
            if path in self._watched_files or path in self._baselines:
                return True
        if self._folder:
            try:
                return Path(path).resolve().is_relative_to(Path(self._folder))  # type: ignore[attr-defined]
            except AttributeError:  # Python < 3.9 fallback
                try:
                    Path(path).resolve().relative_to(Path(self._folder))
                    return Path(path).is_file()
                except ValueError:
                    return False
        return False

    def _handle_path(self, path: str) -> None:
        try:
            path = str(Path(path).resolve())
        except OSError:
            return
        if not self._relevant(path):
            return
        if not Path(path).is_file():
            return
        now = time.monotonic()
        last = self._last_fire.get(path, 0.0)
        if now - last < self._debounce:
            return
        self._last_fire[path] = now
        # Brief settle so writers finish
        time.sleep(self._debounce)
        try:
            current, baseline, matches = self.check_path_now(path)
        except OSError as exc:
            if self._on_alert:
                self._on_alert(path, "", None, f"Monitor error: {exc}")
            return
        if baseline is None:
            msg = f"Baseline set for {path}: {current}"
            if self._on_alert:
                self._on_alert(path, current, None, msg)
            return
        if not matches:
            msg = f"ALERT: hash changed for {path} (was {baseline}, now {current})"
            if self._on_alert:
                self._on_alert(path, current, baseline, msg)
        else:
            msg = f"OK: {path} still matches baseline"
            if self._on_alert:
                self._on_alert(path, current, baseline, msg)


def simulate_monitor_mismatch(
    path: Union[str, Path],
    original_bytes: bytes,
    modified_bytes: bytes,
) -> tuple[str, str, bool]:
    """
    Test helper: write *original_bytes*, baseline, overwrite with *modified_bytes*,
    return (baseline, new_hash, matches).
    """
    path = Path(path)
    path.write_bytes(original_bytes)
    baseline = sha256_file(path)
    path.write_bytes(modified_bytes)
    new_hash = sha256_file(path)
    return baseline, new_hash, compare_hashes(baseline, new_hash)
