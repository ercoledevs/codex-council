#!/usr/bin/env python3
"""Experimental shadow-only Decision Runtime for Codex Council.

The module is deliberately stdlib-only.  It derives a private, transactional
sidecar from existing session artifacts and never writes to the legacy files.
All public operations are explicit; no function makes the runtime authoritative
for a Council verdict or dispatches agents.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import stat
import tempfile
import time
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Union

try:  # POSIX is the supported durability/locking target for v1.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts.
    fcntl = None  # type: ignore[assignment]


RUNTIME_SCHEMA_VERSION = 1
RUNTIME_DIRNAME = "decision-runtime"
RUNTIME_FILE = "runtime.json"
HEAD_FILE = "HEAD"
GENERATIONS_DIR = "generations"
STAGING_DIR = "staging"
QUARANTINE_DIR = "quarantine"

DIRECTORY_MODE = 0o700
FILE_MODE = 0o600
MAX_PATCH_BYTES = 1_048_576
MAX_SOURCE_BYTES = 4_194_304
MAX_GENERATION_BYTES = 16_777_216
MAX_STRING_CHARS = 16_384
MAX_JSON_DEPTH = 16
MAX_PATCH_OPERATIONS = 256
MAX_CELLS = 10_000
MAX_EDGES = 25_000
MAX_DEPENDENCY_DEPTH = 64
DEFAULT_RETENTION_DAYS = 30

CELL_KINDS = {
    "claim",
    "option",
    "counterfactual",
    "evidence",
    "risk",
    "blocker",
    "dissent",
    "verification",
    "decision",
}
CELL_STATES = {
    "open",
    "accepted",
    "rejected",
    "verified",
    "failed",
    "resolved",
    "superseded",
}
CONFIDENCE_LEVELS = {"unknown", "low", "medium", "high"}
SENSITIVITY_LEVELS = {"public", "internal", "restricted"}
RELATIONS = {
    "supports",
    "contradicts",
    "depends_on",
    "supersedes",
    "verifies",
    "derived_from",
}
DAG_RELATIONS = {"depends_on", "supersedes"}
DOMAINS = {
    "architecture",
    "reliability",
    "security",
    "privacy",
    "governance",
    "product",
    "operator",
    "adoption",
    "contrarian",
    "uncertainty",
    "performance",
    "cost",
    "frontend",
    "accessibility",
    "testing",
    "documentation",
}
RISK_FLAGS = {
    "privacy",
    "security",
    "data_loss",
    "frontend_evidence",
    "performance",
    "migration",
    "irreversible",
}
HARD_RISK_FLAGS = {
    "privacy",
    "security",
    "data_loss",
    "frontend_evidence",
    "migration",
    "irreversible",
}
FULL_MEMBERS = ["ada", "grace", "hypatia", "florence", "turing", "seymour"]
DOMAIN_MEMBERS = {
    "architecture": {"ada"},
    "reliability": {"grace"},
    "security": {"hypatia"},
    "privacy": {"hypatia"},
    "governance": {"hypatia"},
    "product": {"florence"},
    "operator": {"florence", "grace"},
    "adoption": {"florence"},
    "contrarian": {"turing"},
    "uncertainty": {"turing"},
    "performance": {"seymour"},
    "cost": {"seymour"},
    "frontend": {"florence"},
    "accessibility": {"florence"},
    "testing": {"grace"},
    "documentation": {"florence"},
}

CELL_FIELDS = {
    "schema_version",
    "cid",
    "kind",
    "state",
    "text",
    "confidence",
    "sensitivity",
    "domains",
    "risk_flags",
    "source_refs",
    "fact_key",
}
CELL_INPUT_FIELDS = {
    "kind",
    "state",
    "text",
    "confidence",
    "sensitivity",
    "domains",
    "risk_flags",
}
EDGE_FIELDS = {"schema_version", "eid", "relation", "from", "to"}
PATCH_FIELDS = {
    "schema_version",
    "patch_id",
    "session_id",
    "base_generation",
    "source_ref",
    "operations",
}
OPERATION_FIELDS = {
    "add_cell": {"op", "local_id", "cell"},
    "add_edge": {"op", "relation", "from", "to"},
    "supersede_cell": {"op", "target", "local_id", "cell"},
}
RUNTIME_FIELDS = {
    "schema_version",
    "session_id",
    "mode",
    "salt",
    "created_at",
    "policy",
}
HEAD_FIELDS = {"schema_version", "generation", "manifest_sha256", "reason"}
MANIFEST_FIELDS = {
    "schema_version",
    "session_id",
    "generation",
    "sequence",
    "parent_generation",
    "created_at",
    "projection_digest",
    "source_manifest",
    "session_metadata",
    "files",
}

MARKDOWN_SECTIONS = {
    "recommendation": "decision",
    "unified proposal": "option",
    "creative proposal": "option",
    "council result": "claim",
    "convergence result": "claim",
    "blocking issues": "blocker",
    "performance blockers": "blocker",
    "risks": "risk",
    "persistent dissent": "dissent",
    "cross-council conflicts": "dissent",
    "verification": "verification",
    "verification required": "verification",
    "verification needed": "verification",
    "measurement required": "verification",
    "missing measurements": "verification",
    "refinements": "option",
    "non-blocking improvements": "option",
}

SOURCE_REF_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
LOCAL_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
CID_RE = re.compile(r"^cell-[0-9a-f]{64}$")
EID_RE = re.compile(r"^edge-[0-9a-f]{64}$")
PATCH_ID_RE = re.compile(r"^patch-[0-9a-f]{64}$")
GENERATION_RE = re.compile(r"^g([0-9]{6})-([0-9a-f]{12})$")
FACT_KEY_RE = re.compile(r"^fact-[0-9a-f]{64}$")

METRICS_FIELDS = {
    "projection_wall_ns",
    "source_files",
    "source_bytes",
    "cell_count",
    "edge_count",
    "frontier_event_count",
    "patch_count",
    "estimated_tokens_only",
}

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "github_token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "bearer": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{16,}=*"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "assigned_secret": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "home_path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
}

FaultHook = Optional[Callable[[str], None]]
PathLike = Union[str, os.PathLike[str], Path]


class DecisionRuntimeError(RuntimeError):
    """Base error for the shadow Decision Runtime."""


class SchemaValidationError(DecisionRuntimeError):
    """An input or persisted record violates the canonical schema."""


class RuntimeSecurityError(DecisionRuntimeError):
    """A path, permission, symlink, privacy, or confinement check failed."""


class RuntimeLockError(DecisionRuntimeError):
    """The single-writer lock could not be acquired."""


class RuntimeConflictError(DecisionRuntimeError):
    """A patch or transaction was based on a stale generation."""


class RuntimeNotInitialized(DecisionRuntimeError):
    """No Decision Runtime exists for this session."""


class PrivacyViolation(RuntimeSecurityError):
    """Potential secret or PII was found before sidecar persistence."""


class InjectedFault(DecisionRuntimeError):
    """Test-only fault raised by a supplied fault hook."""


def _utc_now(now: Optional[datetime] = None) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"invalid UTC timestamp: {value!r}") from exc


def _normalize_string(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if len(normalized) > MAX_STRING_CHARS:
        raise SchemaValidationError(f"string exceeds {MAX_STRING_CHARS} characters")
    return normalized


def _canonical_value(value: Any, depth: int = 0) -> Any:
    if depth > MAX_JSON_DEPTH:
        raise SchemaValidationError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise SchemaValidationError("non-finite JSON numbers are forbidden")
        return value
    if isinstance(value, str):
        return _normalize_string(value)
    if isinstance(value, list):
        return [_canonical_value(item, depth + 1) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise SchemaValidationError("JSON object keys must be strings")
            normalized_key = _normalize_string(key)
            if normalized_key in result:
                raise SchemaValidationError(f"duplicate key after normalization: {normalized_key}")
            result[normalized_key] = _canonical_value(item, depth + 1)
        return result
    raise SchemaValidationError(f"unsupported JSON value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Return the canonical UTF-8 JSON representation used for IDs/checksums."""

    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _reject_constant(value: str) -> None:
    raise SchemaValidationError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SchemaValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(text: str, *, max_bytes: int = MAX_PATCH_BYTES) -> Any:
    """Parse untrusted JSON with duplicate-key, size, depth, and NaN rejection."""

    raw = text.encode("utf-8", errors="strict")
    if len(raw) > max_bytes:
        raise SchemaValidationError(f"JSON input exceeds {max_bytes} bytes")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except SchemaValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(f"invalid JSON: {exc}") from exc
    return _canonical_value(value)


def _unknown_fields(record: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(record) - allowed)
    if unknown:
        raise SchemaValidationError(f"{label} contains unknown fields: {', '.join(unknown)}")


def _require_fields(record: Mapping[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(record))
    if missing:
        raise SchemaValidationError(f"{label} is missing fields: {', '.join(missing)}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac_id(salt: bytes, namespace: str, value: Any) -> str:
    payload = namespace.encode("ascii") + b"\0" + canonical_json(value).encode("utf-8")
    return hmac.new(salt, payload, hashlib.sha256).hexdigest()


def _fault(hook: FaultHook, point: str) -> None:
    if hook is not None:
        hook(point)


def _resolve_session(session_dir: PathLike) -> Path:
    raw = Path(session_dir).expanduser()
    if raw.is_symlink():
        raise RuntimeSecurityError("session directory must not be a symlink")
    try:
        resolved = raw.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"session directory does not exist: {raw}") from exc
    if not resolved.is_dir():
        raise NotADirectoryError(str(resolved))
    return resolved


def runtime_root(session_dir: PathLike) -> Path:
    """Return the confined Decision Runtime sidecar path for a session."""

    return _resolve_session(session_dir) / RUNTIME_DIRNAME


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        return False
    return True


def _assert_confined(path: Path, root: Path) -> None:
    if not _is_within(path, root):
        raise RuntimeSecurityError(f"path escapes runtime root: {path}")


def _check_mode(path: Path, expected: int) -> None:
    if path.is_symlink():
        raise RuntimeSecurityError(f"symlink is forbidden: {path}")
    actual = stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)
    if actual != expected:
        raise RuntimeSecurityError(f"unsafe permissions on {path.name}: {actual:04o}, expected {expected:04o}")


def _make_directory(path: Path, root: Path) -> None:
    _assert_confined(path, root)
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise RuntimeSecurityError(f"runtime directory is unsafe: {path}")
        _check_mode(path, DIRECTORY_MODE)
        return
    path.mkdir(mode=DIRECTORY_MODE)
    os.chmod(path, DIRECTORY_MODE, follow_symlinks=False)
    _check_mode(path, DIRECTORY_MODE)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_new_file(path: Path, data: bytes, root: Path) -> None:
    _assert_confined(path, root)
    if path.exists() or path.is_symlink():
        raise RuntimeSecurityError(f"refusing to replace file with exclusive write: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, FILE_MODE)
    try:
        os.fchmod(fd, FILE_MODE)
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    _check_mode(path, FILE_MODE)


def _atomic_write(path: Path, data: bytes, root: Path) -> None:
    _assert_confined(path, root)
    if path.is_symlink():
        raise RuntimeSecurityError(f"refusing to replace symlink: {path}")
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    _write_new_file(temporary, data, root)
    if path.is_symlink():
        temporary.unlink(missing_ok=True)
        raise RuntimeSecurityError(f"destination became a symlink: {path}")
    os.replace(temporary, path)
    os.chmod(path, FILE_MODE, follow_symlinks=False)
    _fsync_directory(path.parent)


def _safe_read_bytes(path: Path, root: Path, *, max_bytes: int) -> bytes:
    _assert_confined(path, root)
    if path.is_symlink():
        raise RuntimeSecurityError(f"symlink input is forbidden: {path}")
    info = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeSecurityError(f"input is not a regular file: {path}")
    if info.st_size > max_bytes:
        raise SchemaValidationError(f"file exceeds {max_bytes} bytes: {path.name}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(65_536, max_bytes - total + 1))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise SchemaValidationError(f"file exceeds {max_bytes} bytes: {path.name}")
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise RuntimeConflictError(f"source changed while reading: {path.name}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_json_file(path: Path, root: Path, *, max_bytes: int = MAX_PATCH_BYTES) -> Any:
    raw = _safe_read_bytes(path, root, max_bytes=max_bytes)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SchemaValidationError(f"file is not strict UTF-8: {path.name}") from exc
    return strict_json_loads(text, max_bytes=max_bytes)


def _read_jsonl(path: Path, root: Path, *, max_bytes: int = MAX_GENERATION_BYTES) -> list[Any]:
    raw = _safe_read_bytes(path, root, max_bytes=max_bytes)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SchemaValidationError(f"file is not strict UTF-8: {path.name}") from exc
    records: list[Any] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(strict_json_loads(line, max_bytes=max_bytes))
        except SchemaValidationError as exc:
            raise SchemaValidationError(f"{path.name}:{number}: {exc}") from exc
    return records


def _json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    if pretty:
        return (json.dumps(_canonical_value(value), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    return (canonical_json(value) + "\n").encode("utf-8")


def _jsonl_bytes(records: Iterable[Any]) -> bytes:
    return b"".join((canonical_json(record) + "\n").encode("utf-8") for record in records)


def _scan_sensitive(text: str) -> list[str]:
    return sorted(name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text))


def _assert_private_text(text: str) -> None:
    hits = _scan_sensitive(text)
    if hits:
        raise PrivacyViolation("potential secret or PII detected: " + ", ".join(hits))


def _runtime_policy() -> dict[str, Any]:
    return {
        "retention_days": DEFAULT_RETENTION_DAYS,
        "purge_mode": "manual",
        "max_patch_bytes": MAX_PATCH_BYTES,
        "max_generation_bytes": MAX_GENERATION_BYTES,
        "max_operations": MAX_PATCH_OPERATIONS,
        "max_cells": MAX_CELLS,
        "max_edges": MAX_EDGES,
        "max_dependency_depth": MAX_DEPENDENCY_DEPTH,
        "authoritative": False,
        "automatic_rerun": False,
        "automatic_ttl_deletion": False,
    }


def _initialize_runtime(
    session_dir: PathLike,
    *,
    salt_hex: Optional[str] = None,
    now: Optional[datetime] = None,
) -> tuple[Path, dict[str, Any]]:
    session = _resolve_session(session_dir)
    root = session / RUNTIME_DIRNAME
    if root.is_symlink():
        raise RuntimeSecurityError("runtime root must not be a symlink")
    if not root.exists():
        root.mkdir(mode=DIRECTORY_MODE)
        os.chmod(root, DIRECTORY_MODE, follow_symlinks=False)
        _fsync_directory(session)
    _check_mode(root, DIRECTORY_MODE)
    for name in (GENERATIONS_DIR, STAGING_DIR, QUARANTINE_DIR):
        _make_directory(root / name, root)
    runtime_path = root / RUNTIME_FILE
    if runtime_path.exists():
        runtime = _read_json_file(runtime_path, root)
        _validate_runtime_config(runtime, session.name)
        _check_mode(runtime_path, FILE_MODE)
        return root, runtime
    if salt_hex is None:
        salt_hex = os.urandom(32).hex()
    if not re.fullmatch(r"[0-9a-f]{64}", salt_hex):
        raise SchemaValidationError("runtime salt must be 32 bytes of lowercase hex")
    runtime = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "session_id": session.name,
        "mode": "shadow",
        "salt": salt_hex,
        "created_at": _utc_now(now),
        "policy": _runtime_policy(),
    }
    try:
        _write_new_file(runtime_path, _json_bytes(runtime, pretty=True), root)
        _fsync_directory(root)
    except RuntimeSecurityError:
        if not runtime_path.exists():
            raise
        runtime = _read_json_file(runtime_path, root)
        _validate_runtime_config(runtime, session.name)
    return root, runtime


def _validate_runtime_config(runtime: Any, session_id: str) -> None:
    if not isinstance(runtime, dict):
        raise SchemaValidationError("runtime.json must contain an object")
    _unknown_fields(runtime, RUNTIME_FIELDS, "runtime.json")
    _require_fields(runtime, RUNTIME_FIELDS, "runtime.json")
    if runtime["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise SchemaValidationError("unknown Decision Runtime schema version")
    if runtime["session_id"] != session_id:
        raise RuntimeSecurityError("runtime session id does not match directory")
    if runtime["mode"] != "shadow":
        raise RuntimeSecurityError("Decision Runtime v1 is shadow-only")
    if not isinstance(runtime["salt"], str) or not re.fullmatch(r"[0-9a-f]{64}", runtime["salt"]):
        raise SchemaValidationError("invalid session salt")
    _parse_timestamp(runtime["created_at"])
    if runtime["policy"] != _runtime_policy():
        raise RuntimeSecurityError("runtime policy does not match the v1 safety policy")


def _load_runtime(session_dir: PathLike) -> tuple[Path, dict[str, Any]]:
    session = _resolve_session(session_dir)
    root = session / RUNTIME_DIRNAME
    if not root.exists():
        raise RuntimeNotInitialized(f"Decision Runtime not initialized: {root}")
    if root.is_symlink():
        raise RuntimeSecurityError("runtime root must not be a symlink")
    _check_mode(root, DIRECTORY_MODE)
    runtime = _read_json_file(root / RUNTIME_FILE, root)
    _validate_runtime_config(runtime, session.name)
    _check_mode(root / RUNTIME_FILE, FILE_MODE)
    return root, runtime


@contextmanager
def _writer_lock(root: Path) -> Iterator[None]:
    if fcntl is None:
        raise RuntimeLockError("POSIX flock is required by Decision Runtime v1")
    # Lock the stable session directory inode itself. It remains present when the
    # optional runtime tree is atomically renamed during a full purge, preventing
    # split lock domains without leaving a coordinator artifact behind.
    session = root.parent
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(session, flags)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeLockError("Decision Runtime already has an active writer") from exc
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _salt(runtime: Mapping[str, Any]) -> bytes:
    return bytes.fromhex(str(runtime["salt"]))


def _normal_fact_text(text: str) -> str:
    return re.sub(r"\s+", " ", _normalize_string(text).strip()).rstrip(".").casefold()


def _validate_source_ref(value: Any) -> str:
    if not isinstance(value, str) or not SOURCE_REF_RE.fullmatch(value):
        raise SchemaValidationError(f"invalid source_ref: {value!r}")
    return value


def _reserved_patch_source_ref(value: str) -> bool:
    return value in {"chairman", "metadata", "ledger", "findings"} or value.startswith(("candidate-", "reviewer-"))


def _build_cell(payload: Mapping[str, Any], source_refs: Iterable[str], salt: bytes) -> dict[str, Any]:
    _unknown_fields(payload, CELL_INPUT_FIELDS, "cell input")
    _require_fields(payload, {"kind", "state", "text"}, "cell input")
    kind = payload["kind"]
    state = payload["state"]
    text = payload["text"]
    confidence = payload.get("confidence", "unknown")
    sensitivity = payload.get("sensitivity", "internal")
    raw_domains = payload.get("domains", [])
    raw_risk_flags = payload.get("risk_flags", [])
    refs = sorted(set(_validate_source_ref(value) for value in source_refs))
    if not isinstance(kind, str) or kind not in CELL_KINDS:
        raise SchemaValidationError(f"unknown cell kind: {kind!r}")
    if not isinstance(state, str) or state not in CELL_STATES:
        raise SchemaValidationError(f"unknown cell state: {state!r}")
    if not isinstance(text, str) or not text.strip():
        raise SchemaValidationError("cell text must be a non-empty string")
    text = _normalize_string(text.strip())
    _assert_private_text(text)
    if not isinstance(confidence, str) or confidence not in CONFIDENCE_LEVELS:
        raise SchemaValidationError(f"unknown confidence: {confidence!r}")
    if not isinstance(sensitivity, str) or sensitivity not in SENSITIVITY_LEVELS:
        raise SchemaValidationError(f"unknown sensitivity: {sensitivity!r}")
    if not isinstance(raw_domains, list) or any(not isinstance(value, str) or value not in DOMAINS for value in raw_domains):
        raise SchemaValidationError("cell domains contain unknown values")
    if not isinstance(raw_risk_flags, list) or any(
        not isinstance(value, str) or value not in RISK_FLAGS for value in raw_risk_flags
    ):
        raise SchemaValidationError("cell risk_flags contain unknown values")
    # User-declared metadata can add signal but cannot suppress deterministic
    # hard-risk/domain inference from the persisted text.
    domains = sorted(set(raw_domains) | set(_infer_domains(text, "typed-cell")))
    risk_flags = sorted(set(raw_risk_flags) | set(_infer_risk_flags(text)))
    if not refs:
        raise SchemaValidationError("cell must retain at least one pseudonymous source")
    fact_basis = {"kind": kind, "text": _normal_fact_text(text)}
    fact_key = "fact-" + _hmac_id(salt, "fact-v1", fact_basis)
    body = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "kind": kind,
        "state": state,
        "text": text,
        "confidence": confidence,
        "sensitivity": sensitivity,
        "domains": domains,
        "risk_flags": risk_flags,
        "source_refs": refs,
        "fact_key": fact_key,
    }
    return {"cid": "cell-" + _hmac_id(salt, "cell-v1", body), **body}


def _validate_cell(cell: Any, salt: bytes) -> dict[str, Any]:
    if not isinstance(cell, dict):
        raise SchemaValidationError("cell record must be an object")
    _unknown_fields(cell, CELL_FIELDS, "cell")
    _require_fields(cell, CELL_FIELDS, "cell")
    rebuilt = _build_cell(
        {key: cell[key] for key in CELL_INPUT_FIELDS},
        cell["source_refs"],
        salt,
    )
    if cell["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise SchemaValidationError("unknown cell schema version")
    if not isinstance(cell["cid"], str) or not CID_RE.fullmatch(cell["cid"]):
        raise SchemaValidationError("invalid cell cid")
    if cell["cid"] != rebuilt["cid"] or cell["fact_key"] != rebuilt["fact_key"]:
        raise SchemaValidationError("cell canonical ID mismatch")
    if canonical_json(cell) != canonical_json(rebuilt):
        raise SchemaValidationError("cell is not in canonical form")
    return rebuilt


def _build_edge(source: str, target: str, relation: str, salt: bytes) -> dict[str, Any]:
    if not isinstance(source, str) or not isinstance(target, str) or not CID_RE.fullmatch(source) or not CID_RE.fullmatch(target):
        raise SchemaValidationError("edge endpoints must be canonical cell IDs")
    if source == target:
        raise SchemaValidationError("self edges are forbidden")
    if not isinstance(relation, str) or relation not in RELATIONS:
        raise SchemaValidationError(f"unknown relation: {relation!r}")
    body = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "relation": relation,
        "from": source,
        "to": target,
    }
    return {"eid": "edge-" + _hmac_id(salt, "edge-v1", body), **body}


def _validate_edge(edge: Any, salt: bytes, cell_ids: set[str]) -> dict[str, Any]:
    if not isinstance(edge, dict):
        raise SchemaValidationError("edge record must be an object")
    _unknown_fields(edge, EDGE_FIELDS, "edge")
    _require_fields(edge, EDGE_FIELDS, "edge")
    if edge["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise SchemaValidationError("unknown edge schema version")
    rebuilt = _build_edge(edge["from"], edge["to"], edge["relation"], salt)
    if edge["eid"] != rebuilt["eid"] or not EID_RE.fullmatch(str(edge["eid"])):
        raise SchemaValidationError("edge canonical ID mismatch")
    if edge["from"] not in cell_ids or edge["to"] not in cell_ids:
        raise SchemaValidationError("edge contains a dangling cell reference")
    return rebuilt


def _assert_acyclic(edges: Iterable[Mapping[str, Any]]) -> None:
    graph: dict[str, set[str]] = {}
    for edge in edges:
        if edge["relation"] in DAG_RELATIONS:
            graph.setdefault(str(edge["from"]), set()).add(str(edge["to"]))
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, depth: int) -> None:
        if depth > MAX_DEPENDENCY_DEPTH:
            raise SchemaValidationError("dependency graph exceeds maximum depth")
        if node in visiting:
            raise SchemaValidationError("dependency/supersession cycle detected")
        if node in visited:
            return
        visiting.add(node)
        for target in graph.get(node, set()):
            visit(target, depth + 1)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node, 0)


def _source_paths(session: Path) -> list[Path]:
    candidates: list[Path] = []
    for name in ("session.json", "decision-ledger.json", "findings.jsonl", "final.md"):
        path = session / name
        if path.exists() or path.is_symlink():
            candidates.append(path)
    for folder in ("members", "reviews"):
        directory = session / folder
        if directory.is_symlink():
            raise RuntimeSecurityError(f"legacy source directory must not be a symlink: {folder}")
        if not directory.is_dir():
            continue
        candidates.extend(sorted(directory.glob("*.md")))
    for path in candidates:
        if path.is_symlink():
            raise RuntimeSecurityError(f"legacy source must not be a symlink: {path.relative_to(session)}")
        try:
            path.resolve(strict=True).relative_to(session)
        except (FileNotFoundError, ValueError) as exc:
            raise RuntimeSecurityError(f"legacy source escapes the session: {path}") from exc
    return sorted(set(candidates), key=lambda item: item.relative_to(session).as_posix())


def _source_manifest(session: Path, paths: Optional[list[Path]] = None) -> dict[str, dict[str, Any]]:
    session = _resolve_session(session)
    result: dict[str, dict[str, Any]] = {}
    selected = [path.resolve(strict=True) for path in paths] if paths is not None else _source_paths(session)
    for path in selected:
        raw = _safe_read_bytes(path, session, max_bytes=MAX_SOURCE_BYTES)
        relative = path.relative_to(session).as_posix()
        result[relative] = {"sha256": _sha256(raw), "bytes": len(raw)}
    return result


def _pseudonymous_sources(session: Path, paths: list[Path]) -> tuple[dict[str, str], dict[str, Any]]:
    mapping: dict[str, str] = {}
    audit: dict[str, Any] = {}
    member_index = 0
    reviewer_index = 0
    for path in paths:
        relative = path.relative_to(session).as_posix()
        if relative.startswith("members/"):
            member_index += 1
            source_ref = f"candidate-{chr(96 + member_index)}" if member_index <= 26 else f"candidate-{member_index}"
            kind = "member"
        elif relative.startswith("reviews/"):
            reviewer_index += 1
            source_ref = f"reviewer-{chr(96 + reviewer_index)}" if reviewer_index <= 26 else f"reviewer-{reviewer_index}"
            kind = "reviewer"
        elif relative == "final.md":
            source_ref, kind = "chairman", "synthesis"
        elif relative == "session.json":
            source_ref, kind = "metadata", "session-metadata"
        elif relative == "decision-ledger.json":
            source_ref, kind = "ledger", "structured-legacy"
        else:
            source_ref, kind = "findings", "structured-legacy"
        source_ref = _validate_source_ref(source_ref)
        mapping[relative] = source_ref
        audit[source_ref] = {"kind": kind, "source_path": relative}
    return mapping, audit


def _infer_domains(text: str, source_path: str) -> list[str]:
    haystack = f"{text} {source_path}".casefold()
    patterns = {
        "architecture": r"\b(architect|schema|api|module|dependency|graph)\b",
        "reliability": r"\b(reliab|recovery|rollback|crash|atomic|idempot|lock|fault)\b",
        "security": r"\b(security|secrets?|credentials?|auth(?:entication|orization)?|permissions?|symlink|traversal)\b",
        "privacy": r"\b(privacy|pii|redact|personal data|anonym)\b",
        "governance": r"\b(governance|policy|retention|audit|compliance)\b",
        "product": r"\b(product|user value|workflow|experience)\b",
        "operator": r"\b(operator|runbook|doctor|status|quarantine)\b",
        "adoption": r"\b(adoption|onboarding|discover|junior)\b",
        "contrarian": r"\b(contrarian|counter|alternative|dissent)\b",
        "uncertainty": r"\b(uncertain|unknown|confidence|ambig)\b",
        "performance": r"\b(performance|latency|throughput|cpu|rss|benchmark|p95|p50)\b",
        "cost": r"\b(cost|token|budget|disk|byte)\b",
        "frontend": r"\b(frontend|ui|ux|browser|modal)\b",
        "accessibility": r"\b(accessibility|a11y|keyboard|screen reader)\b",
        "testing": r"\b(test|verification|fixture|replay|coverage)\b",
        "documentation": r"\b(document|readme|docs|copy)\b",
    }
    return sorted(domain for domain, pattern in patterns.items() if re.search(pattern, haystack))


def _infer_risk_flags(text: str) -> list[str]:
    haystack = text.casefold()
    patterns = {
        "privacy": r"\b(privacy|pii|personal data|redact|public link)\b",
        "security": r"\b(security|secrets?|credentials?|auth(?:entication|orization)?|symlink|traversal|permissions?)\b",
        "data_loss": r"\b(data loss|destructive|delete data|corruption)\b",
        "frontend_evidence": r"\b(frontend|ui|ux|browser|accessibility)\b",
        "performance": r"\b(performance|latency|throughput|cpu|rss|p95|p50)\b",
        "migration": r"\b(migration|migrate|schema upgrade)\b",
        "irreversible": r"\b(irreversible|cannot roll back|no rollback)\b",
    }
    return sorted(flag for flag, pattern in patterns.items() if re.search(pattern, haystack))


def _markdown_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current: Optional[tuple[str, list[str]]] = None
    in_fence = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            normalized = re.sub(r"\s+", " ", heading.group(1).strip()).casefold()
            current = (normalized, [])
            sections.append(current)
            continue
        if current is not None and not line.startswith("#"):
            current[1].append(line)
    return [(heading, "\n".join(lines)) for heading, lines in sections]


def _section_items(body: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", line)
        if bullet:
            if current:
                items.append(" ".join(current))
            current = [bullet.group(1).strip()]
        elif line and current:
            current.append(line)
        elif not line and current:
            items.append(" ".join(current))
            current = []
    if current:
        items.append(" ".join(current))
    if items:
        return [re.sub(r"\s+", " ", item).strip() for item in items if item.strip()]
    paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    return paragraphs


def _extract_markdown_facts(text: str, relative: str, source_ref: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for heading, body in _markdown_sections(text):
        kind = MARKDOWN_SECTIONS.get(heading)
        if kind is None:
            continue
        for item in _section_items(body):
            if not item or item == "-":
                continue
            state = "open"
            if kind == "decision":
                state = "accepted"
            facts.append(
                {
                    "kind": kind,
                    "state": state,
                    "text": item,
                    "confidence": "unknown",
                    "sensitivity": "internal",
                    "domains": _infer_domains(item, relative),
                    "risk_flags": _infer_risk_flags(item),
                    "source_ref": source_ref,
                }
            )
    return facts


def _extract_ledger_facts(data: Any, source_ref: str) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise SchemaValidationError("decision-ledger.json must contain an object")
    mapping = {
        "decisions": ("decision", "accepted"),
        "blockers": ("blocker", "open"),
        "dissent": ("dissent", "open"),
        "verification": ("verification", "open"),
    }
    facts: list[dict[str, Any]] = []
    for key, (kind, default_state) in mapping.items():
        values = data.get(key, [])
        if values is None:
            continue
        if not isinstance(values, list):
            raise SchemaValidationError(f"decision ledger field {key} must be a list")
        for value in values:
            if isinstance(value, str):
                text = value
            elif isinstance(value, dict):
                unknown = set(value) - {"claim", "text", "state", "confidence", "sensitivity", "domains", "risk_flags"}
                if unknown:
                    raise SchemaValidationError(f"ledger entry contains unknown fields: {', '.join(sorted(unknown))}")
                text = value.get("claim") or value.get("text")
                state = value.get("state", default_state)
            else:
                raise SchemaValidationError("ledger entries must be strings or objects")
            if not isinstance(text, str) or not text.strip():
                continue
            facts.append(
                {
                    "kind": kind,
                    "state": state if isinstance(value, dict) else default_state,
                    "text": text.strip(),
                    "confidence": value.get("confidence", "unknown") if isinstance(value, dict) else "unknown",
                    "sensitivity": value.get("sensitivity", "internal") if isinstance(value, dict) else "internal",
                    "domains": value.get("domains", _infer_domains(text, "decision-ledger.json")) if isinstance(value, dict) else _infer_domains(text, "decision-ledger.json"),
                    "risk_flags": value.get("risk_flags", _infer_risk_flags(text)) if isinstance(value, dict) else _infer_risk_flags(text),
                    "source_ref": source_ref,
                }
            )
    return facts


def _extract_findings_facts(text: str, source_ref: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = strict_json_loads(line, max_bytes=MAX_SOURCE_BYTES)
        except SchemaValidationError as exc:
            raise SchemaValidationError(f"findings.jsonl:{number}: {exc}") from exc
        if not isinstance(record, dict):
            raise SchemaValidationError(f"findings.jsonl:{number} must contain an object")
        if record.get("kind") == "placeholder":
            continue
        allowed = {"schema_version", "kind", "claim", "text", "source", "state", "confidence", "sensitivity", "domains", "risk_flags"}
        _unknown_fields(record, allowed, f"findings.jsonl:{number}")
        claim = record.get("claim") or record.get("text")
        if not isinstance(claim, str) or not claim.strip():
            continue
        raw_kind = str(record.get("kind", "claim"))
        kind = raw_kind if raw_kind in CELL_KINDS else "claim"
        facts.append(
            {
                "kind": kind,
                "state": record.get("state", "open"),
                "text": claim.strip(),
                "confidence": record.get("confidence", "unknown"),
                "sensitivity": record.get("sensitivity", "internal"),
                "domains": record.get("domains", _infer_domains(claim, "findings.jsonl")),
                "risk_flags": record.get("risk_flags", _infer_risk_flags(claim)),
                "source_ref": source_ref,
            }
        )
    return facts


def _extract_legacy(session: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    paths = _source_paths(session)
    mapping, audit_map = _pseudonymous_sources(session, paths)
    manifest = _source_manifest(session, paths)
    facts: list[dict[str, Any]] = []
    for path in paths:
        relative = path.relative_to(session).as_posix()
        raw = _safe_read_bytes(path, session, max_bytes=MAX_SOURCE_BYTES)
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SchemaValidationError(f"legacy source is not strict UTF-8: {relative}") from exc
        source_ref = mapping[relative]
        if relative == "session.json":
            continue
        if relative == "decision-ledger.json":
            facts.extend(_extract_ledger_facts(strict_json_loads(text, max_bytes=MAX_SOURCE_BYTES), source_ref))
        elif relative == "findings.jsonl":
            facts.extend(_extract_findings_facts(text, source_ref))
        else:
            facts.extend(_extract_markdown_facts(text, relative, source_ref))
    for fact in facts:
        _assert_private_text(str(fact["text"]))
    return facts, audit_map, manifest


def _safe_session_metadata(session: Path) -> dict[str, Any]:
    path = session / "session.json"
    if not path.exists() or path.is_symlink():
        return {"mode": "unknown", "session_type": "unknown", "risk_flags": ["unknown"]}
    try:
        data = _read_json_file(path, session, max_bytes=MAX_SOURCE_BYTES)
    except DecisionRuntimeError:
        return {"mode": "unknown", "session_type": "unknown", "risk_flags": ["unknown"]}
    if not isinstance(data, dict):
        return {"mode": "unknown", "session_type": "unknown", "risk_flags": ["unknown"]}
    route = data.get("route_decision", {})
    route_flags = route.get("risk_flags") if isinstance(route, dict) else None
    flags = [flag for flag in route_flags if isinstance(flag, str)] if isinstance(route_flags, list) else ["unknown"]
    return {
        "mode": str(data.get("mode", "unknown")),
        "session_type": str(data.get("session_type", "general")),
        "risk_flags": sorted(set(flags)),
        "frontend_review": "frontend-ui-ux" in data.get("activation_tags", []) if isinstance(data.get("activation_tags", []), list) else False,
    }


def _cells_from_facts(facts: list[dict[str, Any]], salt: bytes) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for fact in facts:
        key = (str(fact["kind"]), _normal_fact_text(str(fact["text"])))
        if key not in grouped:
            grouped[key] = {
                "kind": fact["kind"],
                "state": fact["state"],
                "text": fact["text"],
                "confidence": fact.get("confidence", "unknown"),
                "sensitivity": fact.get("sensitivity", "internal"),
                "domains": set(fact.get("domains", [])),
                "risk_flags": set(fact.get("risk_flags", [])),
                "source_refs": set(),
            }
        grouped[key]["domains"].update(fact.get("domains", []))
        grouped[key]["risk_flags"].update(fact.get("risk_flags", []))
        grouped[key]["source_refs"].add(fact["source_ref"])
    cells: list[dict[str, Any]] = []
    for key in sorted(grouped):
        value = grouped[key]
        cells.append(
            _build_cell(
                {
                    "kind": value["kind"],
                    "state": value["state"],
                    "text": value["text"],
                    "confidence": value["confidence"],
                    "sensitivity": value["sensitivity"],
                    "domains": sorted(value["domains"]),
                    "risk_flags": sorted(value["risk_flags"]),
                },
                sorted(value["source_refs"]),
                salt,
            )
        )
    return sorted(cells, key=lambda cell: cell["cid"])


def _initial_frontier(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "seq": index,
            "event": "observed",
            "fact_key": cell["fact_key"],
            "cell_id": cell["cid"],
            "kind": cell["kind"],
            "state": cell["state"],
            "text": cell["text"],
            "confidence": cell["confidence"],
            "sensitivity": cell["sensitivity"],
            "domains": cell["domains"],
            "risk_flags": cell["risk_flags"],
            "depends_on": [],
            "source_refs": cell["source_refs"],
        }
        for index, cell in enumerate(cells, 1)
    ]


def _validate_frontier(
    frontier: list[dict[str, Any]],
    cells: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Validate the frontier export against its canonical Cell graph."""

    by_id = {cell["cid"]: cell for cell in cells}
    expected_dependencies: dict[str, set[str]] = {}
    superseded_ids: set[str] = set()
    for edge in edges:
        if edge["relation"] == "depends_on":
            expected_dependencies.setdefault(edge["from"], set()).add(edge["to"])
        elif edge["relation"] == "supersedes":
            superseded_ids.add(edge["to"])
    active: dict[str, dict[str, Any]] = {}
    observed_ids: set[str] = set()
    superseded_events: set[str] = set()
    required = {
        "schema_version",
        "seq",
        "event",
        "fact_key",
        "cell_id",
        "kind",
        "state",
        "text",
        "confidence",
        "sensitivity",
        "domains",
        "risk_flags",
        "depends_on",
        "source_refs",
    }
    for index, event in enumerate(frontier, 1):
        if not isinstance(event, dict):
            raise SchemaValidationError("frontier events must be objects")
        _unknown_fields(event, required, "frontier event")
        _require_fields(event, required, "frontier event")
        if event["schema_version"] != RUNTIME_SCHEMA_VERSION:
            raise SchemaValidationError("unknown frontier schema version")
        if not isinstance(event["seq"], int) or isinstance(event["seq"], bool) or event["seq"] != index:
            raise SchemaValidationError("frontier sequence must be contiguous and one-based")
        if not isinstance(event["event"], str) or event["event"] not in {"observed", "superseded"}:
            raise SchemaValidationError(f"unknown frontier event: {event['event']!r}")
        cell_id = event["cell_id"]
        if not isinstance(cell_id, str) or cell_id not in by_id:
            raise SchemaValidationError("frontier contains a dangling cell reference")
        cell = by_id[cell_id]
        if event["fact_key"] != cell["fact_key"] or not FACT_KEY_RE.fullmatch(str(event["fact_key"])):
            raise SchemaValidationError("frontier fact_key does not match its Cell")
        if event["kind"] != cell["kind"] or event["text"] != cell["text"]:
            raise SchemaValidationError("frontier semantic payload does not match its Cell")
        for field in ("confidence", "sensitivity", "domains", "risk_flags"):
            if event[field] != cell[field]:
                raise SchemaValidationError(f"frontier {field} does not match its Cell")
        if event["source_refs"] != cell["source_refs"]:
            raise SchemaValidationError("frontier source_refs do not match its Cell")
        if not isinstance(event["depends_on"], list) or any(
            not isinstance(value, str) or value not in by_id for value in event["depends_on"]
        ):
            raise SchemaValidationError("frontier dependencies contain a dangling Cell")
        if event["depends_on"] != sorted(set(event["depends_on"])):
            raise SchemaValidationError("frontier dependencies must be canonical")
        _assert_private_text(event["text"])
        if event["event"] == "observed":
            if cell_id in observed_ids:
                raise SchemaValidationError("frontier contains duplicate observed events")
            observed_ids.add(cell_id)
            if event["state"] != cell["state"]:
                raise SchemaValidationError("frontier state does not match its Cell")
            if event["depends_on"] != sorted(expected_dependencies.get(cell_id, set())):
                raise SchemaValidationError("frontier dependencies do not match Cell edges")
            active[cell["fact_key"]] = event
        else:
            if cell_id in superseded_events:
                raise SchemaValidationError("frontier contains duplicate supersession events")
            if event["state"] != "superseded" or event["depends_on"]:
                raise SchemaValidationError("superseded frontier events must be terminal")
            superseded_events.add(cell_id)
            active.pop(cell["fact_key"], None)
    if observed_ids != set(by_id):
        raise SchemaValidationError("frontier must observe every Cell exactly once")
    if superseded_events != superseded_ids:
        raise SchemaValidationError("frontier supersession events do not match Cell edges")
    return active


def _comparison(
    cells: list[dict[str, Any]],
    frontier: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    session_metadata: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    active = _validate_frontier(frontier, cells, edges)
    superseded_ids = {edge["to"] for edge in edges if edge["relation"] == "supersedes"}
    by_kind_cells: dict[str, set[str]] = {}
    by_kind_frontier: dict[str, set[str]] = {}
    for cell in cells:
        if cell["state"] != "superseded" and cell["cid"] not in superseded_ids:
            by_kind_cells.setdefault(cell["kind"], set()).add(cell["fact_key"])
    for event in active.values():
        by_kind_frontier.setdefault(str(event["kind"]), set()).add(str(event["fact_key"]))
    recall: dict[str, float] = {}
    for kind in ("blocker", "dissent", "verification"):
        expected = by_kind_cells.get(kind, set())
        found = by_kind_frontier.get(kind, set())
        recall[kind] = 1.0 if not expected else round(len(expected & found) / len(expected), 6)
    cell_bytes = len(_jsonl_bytes(cells)) + len(_jsonl_bytes(edges))
    frontier_bytes = len(_jsonl_bytes(frontier))
    active_cells = [cell for cell in cells if cell["state"] != "superseded" and cell["cid"] not in superseded_ids]
    cell_dependencies = {
        cell["cid"]: sorted(edge["to"] for edge in edges if edge["relation"] == "depends_on" and edge["from"] == cell["cid"])
        for cell in active_cells
    }
    cell_view = [
        {
            "fact_key": cell["fact_key"],
            "cell_id": cell["cid"],
            "kind": cell["kind"],
            "state": cell["state"],
            "text": cell["text"],
            "confidence": cell["confidence"],
            "sensitivity": cell["sensitivity"],
            "domains": cell["domains"],
            "risk_flags": cell["risk_flags"],
            "depends_on": cell_dependencies[cell["cid"]],
            "source_refs": cell["source_refs"],
        }
        for cell in sorted(active_cells, key=lambda item: item["cid"])
    ]
    frontier_view = [
        {
            key: event[key]
            for key in (
                "fact_key",
                "cell_id",
                "kind",
                "state",
                "text",
                "confidence",
                "sensitivity",
                "domains",
                "risk_flags",
                "depends_on",
                "source_refs",
            )
        }
        for event in sorted(active.values(), key=lambda item: item["cell_id"])
    ]
    unsupported_relations = sorted({edge["relation"] for edge in edges} - {"depends_on", "supersedes"})
    semantic_digests = {
        "cells": _sha256(canonical_json(cell_view).encode("utf-8")),
        "frontier": _sha256(canonical_json(frontier_view).encode("utf-8")),
    }
    semantically_equal = (
        not unsupported_relations
        and all(value == 1.0 for value in recall.values())
        and semantic_digests["cells"] == semantic_digests["frontier"]
    )
    frontier_cell_ids = {event["cell_id"] for event in active.values()}
    frontier_cells = [
        {
            "cid": event["cell_id"],
            "kind": event["kind"],
            "state": event["state"],
            "domains": event["domains"],
            "risk_flags": event["risk_flags"],
        }
        for event in active.values()
    ]
    frontier_edges = [
        edge
        for edge in edges
        if edge["relation"] == "depends_on" and edge["from"] in frontier_cell_ids and edge["to"] in frontier_cell_ids
    ]
    metadata = dict(session_metadata or {})
    cell_plan = plan_impact({"cells": active_cells, "edges": edges}, session_metadata=metadata)
    frontier_plan = plan_impact({"cells": frontier_cells, "edges": frontier_edges}, session_metadata=metadata)
    impact_plan_equivalent = canonical_json(cell_plan) == canonical_json(frontier_plan)
    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "compare": "frontier",
        "semantic_equivalence": semantically_equal,
        "semantic_digests": semantic_digests,
        "impact_plan_equivalence": impact_plan_equivalent,
        "unsupported_relations": unsupported_relations,
        "recall": recall,
        "hard_risk_escalation": any(set(cell["risk_flags"]) & HARD_RISK_FLAGS for cell in cells),
        "complexity": {
            "cells": {"records": len(cells) + len(edges), "bytes": cell_bytes},
            "frontier": {"records": len(frontier), "bytes": frontier_bytes},
        },
        "recommendation": (
            "frontier_export_equivalent"
            if semantically_equal and impact_plan_equivalent
            else "cell_graph_required"
        ),
        "targets_are_hypotheses": True,
    }


def _full_plan(
    changed: list[str],
    closure: list[str],
    reasons: Iterable[str],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    mode = metadata.get("mode")
    reviewers = ["performance-impact-reviewer", "coverage-integrator"]
    if mode == "deep":
        reviewers = ["rubric-reviewer", "bias-auditor", "implementation-gatekeeper", *reviewers]
    frontend = bool(metadata.get("frontend_review")) or "frontend_evidence" in metadata.get("risk_flags", [])
    if frontend:
        reviewers.append("leonardo-ux-ui-critic")
    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "coverage": "full",
        "members": FULL_MEMBERS.copy(),
        "reviewers": reviewers,
        "evidence_runners": ["bob-browser-customer-tester"] if frontend else [],
        "changed_cells": sorted(changed),
        "dependency_closure": sorted(closure),
        "forced_full": True,
        "fallback_reasons": sorted(set(reasons)),
        "advisory_only": True,
        "authoritative": False,
    }


def plan_impact(
    projection: Mapping[str, Any],
    changed_cells: Optional[Iterable[str]] = None,
    *,
    session_metadata: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Create an advisory, deterministic plan; ambiguity always returns full coverage."""

    cells = projection.get("cells", [])
    edges = projection.get("edges", [])
    metadata = dict(session_metadata or projection.get("session_metadata", {}) or {})
    if not isinstance(cells, list) or not isinstance(edges, list):
        return _full_plan([], [], ["invalid_projection"], metadata)
    by_id = {cell.get("cid"): cell for cell in cells if isinstance(cell, dict) and isinstance(cell.get("cid"), str)}
    changed = sorted(set(changed_cells or by_id.keys()))
    reasons: list[str] = []
    if not changed:
        reasons.append("no_changed_cells")
    unknown_changed = [cid for cid in changed if cid not in by_id]
    if unknown_changed:
        reasons.append("unknown_changed_cell")
    session_flags = set(metadata.get("risk_flags", [])) if isinstance(metadata.get("risk_flags", []), list) else {"unknown"}
    if session_flags - RISK_FLAGS:
        reasons.append("unknown_session_risk")
    for flag in sorted(session_flags & HARD_RISK_FLAGS):
        reasons.append(f"hard_risk:{flag}")
    if metadata.get("session_type") in {"forge", "skill", "unknown"}:
        reasons.append("unsupported_session_type")

    dependencies: dict[str, set[str]] = {}
    for edge in edges:
        relation = edge.get("relation") if isinstance(edge, dict) else None
        if not isinstance(relation, str) or relation not in RELATIONS:
            reasons.append("unknown_relation")
            continue
        source, target = edge.get("from"), edge.get("to")
        if source not in by_id or target not in by_id:
            reasons.append("dangling_relation")
            continue
        if edge.get("relation") in {"depends_on", "supersedes"}:
            # Traverse from a changed dependency to every dependent. A change to
            # the dependent itself does not imply that unchanged evidence must be
            # treated as changed.
            dependencies.setdefault(str(target), set()).add(str(source))

    closure: set[str] = set()

    def expand(cid: str, depth: int, trail: set[str]) -> None:
        if depth > MAX_DEPENDENCY_DEPTH:
            reasons.append("dependency_depth_exceeded")
            return
        if cid in trail:
            reasons.append("dependency_cycle")
            return
        if cid in closure:
            return
        closure.add(cid)
        for target in sorted(dependencies.get(cid, set())):
            expand(target, depth + 1, trail | {cid})

    for cid in changed:
        if cid in by_id:
            expand(cid, 0, set())

    members: set[str] = {"ada", "grace", "turing"}
    for cid in sorted(closure):
        cell = by_id[cid]
        kind = cell.get("kind")
        state = cell.get("state")
        domains = cell.get("domains")
        flags = cell.get("risk_flags")
        if not isinstance(kind, str) or kind not in CELL_KINDS or not isinstance(state, str) or state not in CELL_STATES:
            reasons.append("unknown_cell_semantics")
            continue
        if kind in {"blocker", "dissent", "risk"} and state in {"open", "failed"}:
            reasons.append(f"open_{kind}")
        if not isinstance(domains, list) or not domains:
            reasons.append("missing_domain")
        elif any(not isinstance(domain, str) or domain not in DOMAINS for domain in domains):
            reasons.append("unknown_domain")
        else:
            for domain in domains:
                members.update(DOMAIN_MEMBERS[domain])
        if not isinstance(flags, list) or any(not isinstance(flag, str) or flag not in RISK_FLAGS for flag in flags):
            reasons.append("unknown_cell_risk")
        else:
            for flag in sorted(set(flags) & HARD_RISK_FLAGS):
                reasons.append(f"hard_risk:{flag}")
    if len(members) > 4:
        reasons.append("target_panel_too_broad")
    if reasons:
        return _full_plan(changed, sorted(closure), reasons, metadata)
    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "coverage": "targeted",
        "members": sorted(members, key=FULL_MEMBERS.index),
        "reviewers": ["coverage-integrator"],
        "evidence_runners": [],
        "changed_cells": changed,
        "dependency_closure": sorted(closure),
        "forced_full": False,
        "fallback_reasons": [],
        "advisory_only": True,
        "authoritative": False,
    }


def _projection_from_legacy(
    session: Path,
    runtime: Mapping[str, Any],
    *,
    compare: str,
) -> dict[str, Any]:
    if compare != "frontier":
        raise ValueError("Decision Runtime v1 supports only the frontier comparator")
    started = time.perf_counter_ns()
    facts, audit_map, source_manifest = _extract_legacy(session)
    if not facts:
        raise DecisionRuntimeError("legacy session has no completed decision facts to project")
    cells = _cells_from_facts(facts, _salt(runtime))
    edges: list[dict[str, Any]] = []
    frontier = _initial_frontier(cells)
    metadata = _safe_session_metadata(session)
    projection: dict[str, Any] = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "session_id": session.name,
        "cells": cells,
        "edges": edges,
        "frontier": frontier,
        "patches": [],
        "comparison": _comparison(cells, frontier, edges, metadata),
        "impact_plan": {},
        "audit_map": audit_map,
        "metrics": {
            "projection_wall_ns": time.perf_counter_ns() - started,
            "source_files": len(source_manifest),
            "source_bytes": sum(item["bytes"] for item in source_manifest.values()),
            "cell_count": len(cells),
            "edge_count": 0,
            "frontier_event_count": len(frontier),
            "estimated_tokens_only": True,
        },
        "source_manifest": source_manifest,
        "session_metadata": metadata,
    }
    projection["impact_plan"] = plan_impact(projection, session_metadata=metadata)
    return projection


def _validate_audit_map(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaValidationError("audit_map must be an object")
    result: dict[str, Any] = {}
    for source_ref, entry in value.items():
        _validate_source_ref(source_ref)
        if not isinstance(entry, dict):
            raise SchemaValidationError("audit map entries must be objects")
        _unknown_fields(entry, {"kind", "source_path"}, "audit map entry")
        _require_fields(entry, {"kind", "source_path"}, "audit map entry")
        if not isinstance(entry["kind"], str) or not entry["kind"]:
            raise SchemaValidationError("audit map kind must be a string")
        source_path = entry["source_path"]
        if not isinstance(source_path, str) or not source_path:
            raise SchemaValidationError("audit map source_path must be a string")
        path = Path(source_path)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeSecurityError("audit map paths must remain relative and confined")
        _assert_private_text(source_path)
        result[source_ref] = {"kind": entry["kind"], "source_path": path.as_posix()}
    return dict(sorted(result.items()))


def _validate_source_manifest(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise SchemaValidationError("source_manifest must be an object")
    result: dict[str, dict[str, Any]] = {}
    for name, item in value.items():
        if not isinstance(name, str) or not name:
            raise SchemaValidationError("source manifest paths must be strings")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeSecurityError("source manifest path escapes session")
        _assert_private_text(path.as_posix())
        if not isinstance(item, dict):
            raise SchemaValidationError("source manifest entry must be an object")
        _unknown_fields(item, {"sha256", "bytes"}, "source manifest entry")
        _require_fields(item, {"sha256", "bytes"}, "source manifest entry")
        if not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise SchemaValidationError("invalid source SHA-256")
        if not isinstance(item["bytes"], int) or isinstance(item["bytes"], bool) or item["bytes"] < 0:
            raise SchemaValidationError("invalid source byte count")
        result[path.as_posix()] = {"sha256": item["sha256"], "bytes": item["bytes"]}
    return dict(sorted(result.items()))


def _validate_metrics(value: Any, *, cells: int, edges: int, frontier: int, patches: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaValidationError("metrics must be an object")
    _unknown_fields(value, METRICS_FIELDS, "metrics")
    required = METRICS_FIELDS - {"patch_count"}
    _require_fields(value, required, "metrics")
    result: dict[str, Any] = {}
    for key in METRICS_FIELDS - {"estimated_tokens_only"}:
        if key not in value:
            continue
        item = value[key]
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise SchemaValidationError(f"metric {key} must be a non-negative integer")
        result[key] = item
    if value["estimated_tokens_only"] is not True:
        raise SchemaValidationError("metrics must identify token figures as estimates")
    result["estimated_tokens_only"] = True
    expected_counts = {
        "cell_count": cells,
        "edge_count": edges,
        "frontier_event_count": frontier,
        "patch_count": patches,
    }
    for key, expected in expected_counts.items():
        if key == "patch_count" and key not in result and expected == 0:
            continue
        if result.get(key) != expected:
            raise SchemaValidationError(f"metric {key} does not match projection content")
    return result


def _validate_projection(projection: Mapping[str, Any], runtime: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "session_id",
        "cells",
        "edges",
        "frontier",
        "patches",
        "comparison",
        "impact_plan",
        "audit_map",
        "metrics",
        "source_manifest",
        "session_metadata",
        "generation",
        "manifest",
        "manifest_sha256",
        "head_reason",
    }
    _unknown_fields(projection, allowed, "projection")
    required = allowed - {"generation", "manifest", "manifest_sha256", "head_reason"}
    _require_fields(projection, required, "projection")
    if projection["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise SchemaValidationError("unknown projection schema version")
    if not isinstance(projection["session_id"], str) or projection["session_id"] != runtime["session_id"]:
        raise RuntimeSecurityError("projection session id mismatch")
    raw_cells = projection["cells"]
    raw_edges = projection["edges"]
    raw_frontier = projection["frontier"]
    raw_patches = projection["patches"]
    if not isinstance(raw_cells, list) or not isinstance(raw_edges, list) or not isinstance(raw_frontier, list):
        raise SchemaValidationError("cells, edges, and frontier must be arrays")
    if not isinstance(raw_patches, list):
        raise SchemaValidationError("patches must be an array")
    if len(raw_cells) > MAX_CELLS:
        raise SchemaValidationError(f"projection exceeds {MAX_CELLS} cells")
    if len(raw_edges) > MAX_EDGES:
        raise SchemaValidationError(f"projection exceeds {MAX_EDGES} edges")
    salt = _salt(runtime)
    cells = sorted((_validate_cell(cell, salt) for cell in raw_cells), key=lambda item: item["cid"])
    cell_ids = {cell["cid"] for cell in cells}
    if len(cell_ids) != len(cells):
        raise SchemaValidationError("duplicate cell IDs")
    edges = sorted((_validate_edge(edge, salt, cell_ids) for edge in raw_edges), key=lambda item: item["eid"])
    if len({edge["eid"] for edge in edges}) != len(edges):
        raise SchemaValidationError("duplicate edge IDs")
    _assert_acyclic(edges)
    frontier = [_canonical_value(event) for event in raw_frontier]
    _validate_frontier(frontier, cells, edges)
    audit_map = _validate_audit_map(projection["audit_map"])
    for cell in cells:
        missing_refs = sorted(set(cell["source_refs"]) - set(audit_map))
        if missing_refs:
            raise SchemaValidationError("Cell source_refs are missing from the audit map")
    source_manifest = _validate_source_manifest(projection["source_manifest"])
    session_metadata = projection["session_metadata"]
    if not isinstance(session_metadata, dict):
        raise SchemaValidationError("session_metadata must be an object")
    safe_metadata_fields = {"mode", "session_type", "risk_flags", "frontend_review"}
    _unknown_fields(session_metadata, safe_metadata_fields, "session_metadata")
    _require_fields(session_metadata, safe_metadata_fields, "session_metadata")
    if session_metadata["mode"] not in {"fast", "standard", "deep", "unknown"}:
        raise SchemaValidationError("session_metadata mode is invalid")
    if session_metadata["session_type"] not in {
        "general",
        "architecture",
        "implementation",
        "decision",
        "skill",
        "frontend",
        "forge",
        "unknown",
    }:
        raise SchemaValidationError("session_metadata session_type is invalid")
    if not isinstance(session_metadata["risk_flags"], list) or any(
        not isinstance(flag, str) or flag not in RISK_FLAGS | {"unknown"}
        for flag in session_metadata["risk_flags"]
    ):
        raise SchemaValidationError("session_metadata risk_flags are invalid")
    if not isinstance(session_metadata["frontend_review"], bool):
        raise SchemaValidationError("session_metadata frontend_review must be boolean")
    validated_patches: list[dict[str, Any]] = []
    patch_ids: set[str] = set()
    for patch in raw_patches:
        if not isinstance(patch, dict):
            raise SchemaValidationError("persisted patches must be objects")
        base_generation = patch.get("base_generation")
        if not isinstance(base_generation, str):
            raise SchemaValidationError("persisted patch base_generation is invalid")
        canonical_patch = _canonical_patch(
            patch,
            runtime=runtime,
            current_generation=base_generation,
            allow_stale=True,
        )
        if canonical_json(canonical_patch) != canonical_json(patch):
            raise SchemaValidationError("persisted patch is not canonical")
        if canonical_patch["patch_id"] in patch_ids:
            raise SchemaValidationError("duplicate persisted patch ID")
        patch_ids.add(canonical_patch["patch_id"])
        validated_patches.append(canonical_patch)
        audit_entry = audit_map.get(canonical_patch["source_ref"])
        if not isinstance(audit_entry, dict) or audit_entry.get("kind") != "typed-patch":
            raise RuntimeSecurityError("Decision Patch provenance must map to a typed-patch audit entry")
    expected_edge_ids: set[str] = set()
    superseded_targets: set[str] = set()
    for patch in validated_patches:
        patch_edges, patch_superseded = _validate_patch_effects(patch, runtime, cell_ids)
        if superseded_targets & patch_superseded:
            raise SchemaValidationError("a Cell may be superseded only once across the patch chain")
        superseded_targets.update(patch_superseded)
        expected_edge_ids.update(patch_edges)
    if {edge["eid"] for edge in edges} != expected_edge_ids:
        raise SchemaValidationError("Cell edges do not match the persisted Decision Patch chain")
    metrics = _validate_metrics(
        projection["metrics"],
        cells=len(cells),
        edges=len(edges),
        frontier=len(frontier),
        patches=len(validated_patches),
    )
    result = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "session_id": runtime["session_id"],
        "cells": cells,
        "edges": edges,
        "frontier": frontier,
        "patches": validated_patches,
        "comparison": _comparison(cells, frontier, edges, session_metadata),
        "impact_plan": {},
        "audit_map": audit_map,
        "metrics": metrics,
        "source_manifest": source_manifest,
        "session_metadata": _canonical_value(session_metadata),
    }
    changed = _patch_changed_cells(validated_patches[-1], runtime) if validated_patches else None
    result["impact_plan"] = plan_impact(result, changed_cells=changed, session_metadata=session_metadata)
    return result


def _projection_files(projection: Mapping[str, Any]) -> dict[str, bytes]:
    return {
        "cells.jsonl": _jsonl_bytes(projection["cells"]),
        "edges.jsonl": _jsonl_bytes(projection["edges"]),
        "patches.jsonl": _jsonl_bytes(projection["patches"]),
        "frontier.jsonl": _jsonl_bytes(projection["frontier"]),
        "comparison.json": _json_bytes(projection["comparison"], pretty=True),
        "impact-plan.json": _json_bytes(projection["impact_plan"], pretty=True),
        "audit-map.json": _json_bytes(projection["audit_map"], pretty=True),
        "metrics.json": _json_bytes(projection["metrics"], pretty=True),
    }


def _semantic_projection_digest(projection: Mapping[str, Any]) -> str:
    semantic = {
        "cells": projection["cells"],
        "edges": projection["edges"],
        "patches": projection["patches"],
        "frontier": projection["frontier"],
        "comparison": projection["comparison"],
        "impact_plan": projection["impact_plan"],
        "audit_map": projection["audit_map"],
        "source_manifest": projection["source_manifest"],
        "session_metadata": projection["session_metadata"],
    }
    return _sha256(canonical_json(semantic).encode("utf-8"))


def _head_path(root: Path) -> Path:
    return root / HEAD_FILE


def _validate_head(head: Any) -> dict[str, Any]:
    if not isinstance(head, dict):
        raise SchemaValidationError("HEAD must contain an object")
    _unknown_fields(head, HEAD_FIELDS, "HEAD")
    _require_fields(head, HEAD_FIELDS, "HEAD")
    if head["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise SchemaValidationError("unknown HEAD schema version")
    if not isinstance(head["generation"], str) or not GENERATION_RE.fullmatch(head["generation"]):
        raise SchemaValidationError("invalid HEAD generation")
    if not isinstance(head["manifest_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", head["manifest_sha256"]):
        raise SchemaValidationError("invalid HEAD manifest checksum")
    if not isinstance(head["reason"], str) or head["reason"] not in {"commit", "recovery", "rollback"}:
        raise SchemaValidationError("invalid HEAD reason")
    return dict(head)


def _read_head(root: Path) -> Optional[dict[str, Any]]:
    path = _head_path(root)
    if not path.exists():
        return None
    _check_mode(path, FILE_MODE)
    return _validate_head(_read_json_file(path, root))


def _write_head(root: Path, generation: str, manifest_sha256: str, reason: str, hook: FaultHook = None) -> dict[str, Any]:
    head = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "generation": generation,
        "manifest_sha256": manifest_sha256,
        "reason": reason,
    }
    _fault(hook, "before_head_replace")
    _atomic_write(_head_path(root), _json_bytes(head, pretty=True), root)
    _fault(hook, "after_head_replace")
    return head


def _validate_manifest(manifest: Any, expected_generation: str, session_id: str) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise SchemaValidationError("generation manifest must be an object")
    _unknown_fields(manifest, MANIFEST_FIELDS, "generation manifest")
    _require_fields(manifest, MANIFEST_FIELDS, "generation manifest")
    if manifest["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise SchemaValidationError("unknown generation manifest schema")
    if manifest["session_id"] != session_id or manifest["generation"] != expected_generation:
        raise RuntimeSecurityError("generation manifest identity mismatch")
    if not isinstance(manifest["sequence"], int) or isinstance(manifest["sequence"], bool) or manifest["sequence"] < 1:
        raise SchemaValidationError("invalid generation sequence")
    match = GENERATION_RE.fullmatch(expected_generation)
    if match is None or int(match.group(1)) != manifest["sequence"]:
        raise SchemaValidationError("generation sequence/name mismatch")
    parent = manifest["parent_generation"]
    if parent is not None and (not isinstance(parent, str) or not GENERATION_RE.fullmatch(parent)):
        raise SchemaValidationError("invalid parent generation")
    _parse_timestamp(manifest["created_at"])
    if not isinstance(manifest["projection_digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", manifest["projection_digest"]):
        raise SchemaValidationError("invalid projection digest")
    _validate_source_manifest(manifest["source_manifest"])
    if not isinstance(manifest["session_metadata"], dict):
        raise SchemaValidationError("manifest session_metadata must be an object")
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        raise SchemaValidationError("manifest files must be a non-empty object")
    expected_files = {
        "cells.jsonl",
        "edges.jsonl",
        "patches.jsonl",
        "frontier.jsonl",
        "comparison.json",
        "impact-plan.json",
        "audit-map.json",
        "metrics.json",
    }
    if set(files) != expected_files:
        raise SchemaValidationError("generation manifest has an unexpected file set")
    for name, entry in files.items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise RuntimeSecurityError("manifest file path escapes generation")
        if not isinstance(entry, dict):
            raise SchemaValidationError("manifest file entries must be objects")
        _unknown_fields(entry, {"sha256", "bytes"}, "manifest file entry")
        _require_fields(entry, {"sha256", "bytes"}, "manifest file entry")
        if not re.fullmatch(r"[0-9a-f]{64}", str(entry["sha256"])):
            raise SchemaValidationError("invalid manifest file checksum")
        if not isinstance(entry["bytes"], int) or isinstance(entry["bytes"], bool) or entry["bytes"] < 0:
            raise SchemaValidationError("invalid manifest file size")
    return dict(manifest)


def _generation_path(root: Path, generation: str) -> Path:
    if not GENERATION_RE.fullmatch(generation):
        raise SchemaValidationError("invalid generation name")
    return root / GENERATIONS_DIR / generation


def _load_generation(root: Path, runtime: Mapping[str, Any], generation: str) -> dict[str, Any]:
    directory = _generation_path(root, generation)
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeSecurityError(f"generation is missing or unsafe: {generation}")
    _check_mode(directory, DIRECTORY_MODE)
    for marker_name in ("PREPARED", "VALIDATED"):
        marker_path = directory / marker_name
        if not marker_path.exists():
            raise SchemaValidationError(f"generation is missing {marker_name}")
        _check_mode(marker_path, FILE_MODE)
        marker = _read_json_file(marker_path, root)
        if marker != {"schema_version": RUNTIME_SCHEMA_VERSION, "generation": generation}:
            raise SchemaValidationError(f"invalid {marker_name} marker")
    committed_path = directory / "COMMITTED"
    if not committed_path.exists():
        raise SchemaValidationError(f"generation is not committed: {generation}")
    _check_mode(committed_path, FILE_MODE)
    manifest_path = directory / "manifest.json"
    _check_mode(manifest_path, FILE_MODE)
    manifest_raw = _safe_read_bytes(manifest_path, root, max_bytes=MAX_GENERATION_BYTES)
    manifest = _validate_manifest(strict_json_loads(manifest_raw.decode("utf-8"), max_bytes=MAX_GENERATION_BYTES), generation, runtime["session_id"])
    manifest_digest = _sha256(manifest_raw)
    committed = _read_json_file(committed_path, root)
    if not isinstance(committed, dict) or set(committed) != {"schema_version", "generation", "manifest_sha256"}:
        raise SchemaValidationError("invalid COMMITTED marker")
    if committed != {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "generation": generation,
        "manifest_sha256": manifest_digest,
    }:
        raise SchemaValidationError("COMMITTED marker checksum mismatch")
    total = 0
    for name, expected in manifest["files"].items():
        path = directory / name
        _check_mode(path, FILE_MODE)
        raw = _safe_read_bytes(path, root, max_bytes=MAX_GENERATION_BYTES)
        total += len(raw)
        if len(raw) != expected["bytes"] or _sha256(raw) != expected["sha256"]:
            raise SchemaValidationError(f"generation checksum mismatch: {name}")
    if total > MAX_GENERATION_BYTES:
        raise SchemaValidationError("generation exceeds byte quota")
    cells = _read_jsonl(directory / "cells.jsonl", root)
    edges = _read_jsonl(directory / "edges.jsonl", root)
    frontier = _read_jsonl(directory / "frontier.jsonl", root)
    patches = _read_jsonl(directory / "patches.jsonl", root)
    projection = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "session_id": runtime["session_id"],
        "cells": cells,
        "edges": edges,
        "frontier": frontier,
        "patches": patches,
        "comparison": _read_json_file(directory / "comparison.json", root),
        "impact_plan": _read_json_file(directory / "impact-plan.json", root),
        "audit_map": _read_json_file(directory / "audit-map.json", root),
        "metrics": _read_json_file(directory / "metrics.json", root),
        "source_manifest": manifest["source_manifest"],
        "session_metadata": manifest["session_metadata"],
    }
    validated = _validate_projection(projection, runtime)
    if _semantic_projection_digest(validated) != manifest["projection_digest"]:
        raise SchemaValidationError("projection semantic digest mismatch")
    validated["generation"] = generation
    validated["manifest"] = manifest
    validated["manifest_sha256"] = manifest_digest
    return validated


def _next_sequence(root: Path) -> int:
    highest = 0
    directory = root / GENERATIONS_DIR
    for path in directory.iterdir():
        match = GENERATION_RE.fullmatch(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def commit_projection(
    session_dir: PathLike,
    projection: Mapping[str, Any],
    *,
    parent_generation: Optional[str] = None,
    require_parent_match: bool = True,
    fault_hook: FaultHook = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Atomically commit a validated shadow projection and advance HEAD."""

    session = _resolve_session(session_dir)
    root, runtime = _initialize_runtime(session, now=now)
    validated = _validate_projection(projection, runtime)
    files = _projection_files(validated)
    if sum(len(value) for value in files.values()) > MAX_GENERATION_BYTES:
        raise SchemaValidationError("projection exceeds generation byte quota")
    with _writer_lock(root):
        if _source_manifest(session) != validated["source_manifest"]:
            raise RuntimeConflictError("legacy artifacts changed since projection; project again before committing")
        current_head = _read_head(root)
        current_generation = current_head["generation"] if current_head else None
        if (require_parent_match or parent_generation is not None) and parent_generation != current_generation:
            raise RuntimeConflictError("parent generation is stale")
        if current_head is not None:
            current = _load_generation(root, runtime, current_generation)
            current_patches = current["patches"]
            candidate_patches = validated["patches"]
            same_history = canonical_json(candidate_patches) == canonical_json(current_patches)
            valid_append = (
                len(candidate_patches) == len(current_patches) + 1
                and canonical_json(candidate_patches[:-1]) == canonical_json(current_patches)
                and candidate_patches[-1]["base_generation"] == current_generation
            )
            if not same_history and not valid_append:
                raise RuntimeConflictError("Decision Patch history must be an ordered single-generation append")
            if current["manifest"]["projection_digest"] == _semantic_projection_digest(validated):
                return {
                    "ok": True,
                    "status": "healthy",
                    "generation": current_generation,
                    "parent_generation": current["manifest"]["parent_generation"],
                    "idempotent": True,
                    "authoritative": False,
                }
        elif validated["patches"]:
            raise RuntimeConflictError("the first shadow generation cannot contain Decision Patches")
        sequence = _next_sequence(root)
        projection_digest = _semantic_projection_digest(validated)
        generation = f"g{sequence:06d}-{projection_digest[:12]}"
        staging = root / STAGING_DIR / f"tx-{uuid.uuid4().hex}"
        _make_directory(staging, root)
        _write_new_file(staging / "PREPARED", _json_bytes({"schema_version": 1, "generation": generation}), root)
        _fault(fault_hook, "after_prepared")
        file_manifest: dict[str, Any] = {}
        for name, raw in files.items():
            _write_new_file(staging / name, raw, root)
            file_manifest[name] = {"sha256": _sha256(raw), "bytes": len(raw)}
            _fault(fault_hook, f"after_write_{name.replace('.', '_').replace('-', '_')}")
        manifest = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "session_id": runtime["session_id"],
            "generation": generation,
            "sequence": sequence,
            "parent_generation": current_generation,
            "created_at": _utc_now(now),
            "projection_digest": projection_digest,
            "source_manifest": validated["source_manifest"],
            "session_metadata": validated["session_metadata"],
            "files": file_manifest,
        }
        manifest_raw = _json_bytes(manifest, pretty=True)
        _write_new_file(staging / "manifest.json", manifest_raw, root)
        _fault(fault_hook, "after_manifest")
        _validate_manifest(manifest, generation, runtime["session_id"])
        for name, expected in file_manifest.items():
            raw = _safe_read_bytes(staging / name, root, max_bytes=MAX_GENERATION_BYTES)
            if _sha256(raw) != expected["sha256"] or len(raw) != expected["bytes"]:
                raise SchemaValidationError(f"staged file failed validation: {name}")
        _write_new_file(staging / "VALIDATED", _json_bytes({"schema_version": 1, "generation": generation}), root)
        _fsync_directory(staging)
        _fault(fault_hook, "after_validated")
        destination = _generation_path(root, generation)
        if destination.exists() or destination.is_symlink():
            raise RuntimeConflictError(f"generation already exists: {generation}")
        os.rename(staging, destination)
        _fsync_directory(root / GENERATIONS_DIR)
        _fault(fault_hook, "after_generation_rename")
        manifest_digest = _sha256(manifest_raw)
        committed = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "generation": generation,
            "manifest_sha256": manifest_digest,
        }
        _write_new_file(destination / "COMMITTED", _json_bytes(committed, pretty=True), root)
        _fsync_directory(destination)
        _fault(fault_hook, "after_committed")
        if _source_manifest(session) != validated["source_manifest"]:
            _quarantine_path(root, destination, "legacy-source-changed")
            raise RuntimeConflictError("legacy artifacts changed during commit; HEAD was not advanced")
        _write_head(root, generation, manifest_digest, "commit", fault_hook)
        return {
            "ok": True,
            "status": "healthy",
            "generation": generation,
            "parent_generation": current_generation,
            "idempotent": False,
            "projection_digest": projection_digest,
            "authoritative": False,
        }


def project_session(
    session_dir: PathLike,
    *,
    compare: str = "frontier",
    commit: bool = True,
    fault_hook: FaultHook = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Derive Cell and frontier representations from legacy artifacts.

    Legacy source hashes are checked before and after projection.  Only the
    private sidecar may be created or updated.
    """

    session = _resolve_session(session_dir)
    source_before = _source_manifest(session)
    root, runtime = _initialize_runtime(session, now=now)
    observed_head = _read_head(root)
    observed_generation = observed_head["generation"] if observed_head else None
    observed_projection = _load_generation(root, runtime, observed_generation) if observed_generation else None
    projection = _projection_from_legacy(session, runtime, compare=compare)
    source_after = _source_manifest(session)
    if source_before != source_after or source_after != projection["source_manifest"]:
        raise RuntimeConflictError("legacy artifacts changed during shadow projection")
    if not commit:
        return projection
    if observed_projection and observed_projection["patches"]:
        if observed_projection["source_manifest"] == source_after:
            with _writer_lock(root):
                latest_head = _read_head(root)
                if latest_head is None or latest_head["generation"] != observed_generation:
                    raise RuntimeConflictError("HEAD changed during idempotent projection verification")
                latest = _load_generation(root, runtime, observed_generation)
                if _source_manifest(session) != latest["source_manifest"]:
                    raise RuntimeConflictError("legacy artifacts changed during idempotent projection verification")
                return {
                    "ok": True,
                    "status": "healthy",
                    "generation": observed_generation,
                    "parent_generation": latest["manifest"]["parent_generation"],
                    "idempotent": True,
                    "comparison": latest["comparison"],
                    "impact_plan": latest["impact_plan"],
                    "source_files": len(source_after),
                    "patches_preserved": len(latest["patches"]),
                    "authoritative": False,
                }
        raise RuntimeConflictError(
            "legacy artifacts changed after Decision Patches; rollback or explicitly purge the sidecar before re-projecting"
        )
    result = commit_projection(
        session,
        projection,
        parent_generation=observed_generation,
        require_parent_match=True,
        fault_hook=fault_hook,
        now=now,
    )
    result["comparison"] = projection["comparison"]
    result["impact_plan"] = projection["impact_plan"]
    result["source_files"] = len(source_after)
    return result


def load_head_projection(session_dir: PathLike) -> dict[str, Any]:
    """Load and fully verify the immutable projection referenced by HEAD."""

    root, runtime = _load_runtime(session_dir)
    head = _read_head(root)
    if head is None:
        raise RuntimeNotInitialized("Decision Runtime has no committed generation")
    projection = _load_generation(root, runtime, head["generation"])
    if projection["manifest_sha256"] != head["manifest_sha256"]:
        raise SchemaValidationError("HEAD manifest checksum mismatch")
    projection["head_reason"] = head["reason"]
    return projection


def _load_patch_input(patch: Union[PathLike, Mapping[str, Any]]) -> dict[str, Any]:
    if isinstance(patch, Mapping):
        value = _canonical_value(dict(patch))
        if len(canonical_json(value).encode("utf-8")) > MAX_PATCH_BYTES:
            raise SchemaValidationError(f"patch exceeds {MAX_PATCH_BYTES} bytes")
    else:
        path = Path(patch).expanduser()
        if path.is_symlink():
            raise RuntimeSecurityError("patch input must not be a symlink")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            raise RuntimeSecurityError(f"cannot safely open patch input: {path}") from exc
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise RuntimeSecurityError("patch input must be a regular file")
            if before.st_size > MAX_PATCH_BYTES:
                raise SchemaValidationError(f"patch exceeds {MAX_PATCH_BYTES} bytes")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(fd, min(65_536, MAX_PATCH_BYTES - total + 1))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_PATCH_BYTES:
                    raise SchemaValidationError(f"patch exceeds {MAX_PATCH_BYTES} bytes")
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise RuntimeConflictError("patch input changed while reading")
        finally:
            os.close(fd)
        try:
            value = strict_json_loads(b"".join(chunks).decode("utf-8", errors="strict"), max_bytes=MAX_PATCH_BYTES)
        except UnicodeDecodeError as exc:
            raise SchemaValidationError("patch must be strict UTF-8") from exc
    if not isinstance(value, dict):
        raise SchemaValidationError("patch must contain a JSON object")
    return value


def _canonical_patch(
    patch: Mapping[str, Any],
    *,
    runtime: Mapping[str, Any],
    current_generation: str,
    allow_stale: bool = False,
) -> dict[str, Any]:
    _unknown_fields(patch, PATCH_FIELDS, "decision patch")
    required = PATCH_FIELDS - {"patch_id"}
    _require_fields(patch, required, "decision patch")
    if patch["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise SchemaValidationError("unknown decision patch schema")
    if not isinstance(patch["session_id"], str) or patch["session_id"] != runtime["session_id"]:
        raise RuntimeSecurityError("patch session id mismatch")
    if not isinstance(patch["base_generation"], str) or not GENERATION_RE.fullmatch(patch["base_generation"]):
        raise SchemaValidationError("patch base_generation is invalid")
    if not allow_stale and patch["base_generation"] != current_generation:
        raise RuntimeConflictError("patch base_generation is stale")
    source_ref = _validate_source_ref(patch["source_ref"])
    if _reserved_patch_source_ref(source_ref):
        raise RuntimeSecurityError("Decision Patch source_ref collides with reserved legacy provenance")
    operations = patch["operations"]
    if not isinstance(operations, list) or not operations:
        raise SchemaValidationError("patch operations must be a non-empty array")
    if len(operations) > MAX_PATCH_OPERATIONS:
        raise SchemaValidationError(f"patch exceeds {MAX_PATCH_OPERATIONS} operations")
    normalized_operations: list[dict[str, Any]] = []
    local_ids: set[str] = set()
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise SchemaValidationError(f"patch operation {index} must be an object")
        op = operation.get("op")
        if not isinstance(op, str) or op not in OPERATION_FIELDS:
            raise SchemaValidationError(f"unknown patch operation: {op!r}")
        _unknown_fields(operation, OPERATION_FIELDS[op], f"patch operation {op}")
        _require_fields(operation, OPERATION_FIELDS[op], f"patch operation {op}")
        normalized = dict(operation)
        if op in {"add_cell", "supersede_cell"}:
            local_id = operation["local_id"]
            if not isinstance(local_id, str) or not LOCAL_ID_RE.fullmatch(local_id):
                raise SchemaValidationError(f"invalid local_id: {local_id!r}")
            if local_id in local_ids:
                raise SchemaValidationError(f"duplicate local_id: {local_id}")
            local_ids.add(local_id)
            cell_input = operation["cell"]
            if not isinstance(cell_input, dict):
                raise SchemaValidationError("patch cell must be an object")
            _unknown_fields(cell_input, CELL_INPUT_FIELDS, "patch cell")
            _require_fields(cell_input, {"kind", "state", "text"}, "patch cell")
            _assert_private_text(str(cell_input["text"]))
            normalized["cell"] = _canonical_value(cell_input)
        if op == "supersede_cell":
            if not isinstance(operation["target"], str) or not CID_RE.fullmatch(operation["target"]):
                raise SchemaValidationError("supersede target must be a canonical cell ID")
        if op == "add_edge":
            if not isinstance(operation["relation"], str) or operation["relation"] not in RELATIONS:
                raise SchemaValidationError("patch contains an unknown relation")
            if operation["relation"] == "supersedes":
                raise SchemaValidationError("use supersede_cell so frontier and Cell state advance together")
            for endpoint in (operation["from"], operation["to"]):
                if not isinstance(endpoint, str) or not (
                    CID_RE.fullmatch(endpoint) or (endpoint.startswith("$") and LOCAL_ID_RE.fullmatch(endpoint[1:]))
                ):
                    raise SchemaValidationError(f"invalid patch edge endpoint: {endpoint!r}")
        normalized_operations.append(_canonical_value(normalized))
    body = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "session_id": runtime["session_id"],
        "base_generation": patch["base_generation"],
        "source_ref": source_ref,
        "operations": normalized_operations,
    }
    computed = "patch-" + _hmac_id(_salt(runtime), "patch-v1", body)
    supplied = patch.get("patch_id")
    if supplied is not None and (not isinstance(supplied, str) or not PATCH_ID_RE.fullmatch(supplied) or supplied != computed):
        raise SchemaValidationError("patch_id does not match canonical patch content")
    return {"patch_id": computed, **body}


def _patch_changed_cells(patch: Mapping[str, Any], runtime: Mapping[str, Any]) -> list[str]:
    """Derive a conservative changed set from canonical patch operations."""

    aliases: dict[str, str] = {}
    changed: set[str] = set()
    for operation in patch["operations"]:
        if operation["op"] in {"add_cell", "supersede_cell"}:
            cell = _build_cell(operation["cell"], [patch["source_ref"]], _salt(runtime))
            aliases[operation["local_id"]] = cell["cid"]
            changed.add(cell["cid"])
            if operation["op"] == "supersede_cell":
                changed.add(operation["target"])
    for operation in patch["operations"]:
        if operation["op"] != "add_edge":
            continue
        for endpoint in (operation["from"], operation["to"]):
            if endpoint.startswith("$"):
                alias = endpoint[1:]
                if alias not in aliases:
                    raise SchemaValidationError(f"patch references unknown local alias: {endpoint}")
                endpoint = aliases[alias]
            changed.add(endpoint)
    return sorted(changed)


def _validate_patch_effects(
    patch: Mapping[str, Any],
    runtime: Mapping[str, Any],
    cell_ids: set[str],
) -> tuple[set[str], set[str]]:
    """Prove that typed operations reduce to Cells/edges present in a projection."""

    aliases: dict[str, str] = {}
    expected_edges: set[str] = set()
    superseded_targets: set[str] = set()
    for operation in patch["operations"]:
        if operation["op"] not in {"add_cell", "supersede_cell"}:
            continue
        cell = _build_cell(operation["cell"], [patch["source_ref"]], _salt(runtime))
        aliases[operation["local_id"]] = cell["cid"]
        if cell["cid"] not in cell_ids:
            raise SchemaValidationError("Decision Patch cell is missing from the reduced projection")
        if operation["op"] == "supersede_cell":
            target = operation["target"]
            if target not in cell_ids:
                raise SchemaValidationError("Decision Patch supersession target is missing")
            superseded_targets.add(target)
            expected_edges.add(_build_edge(cell["cid"], target, "supersedes", _salt(runtime))["eid"])

    def resolve(endpoint: str) -> str:
        if endpoint.startswith("$"):
            alias = endpoint[1:]
            if alias not in aliases:
                raise SchemaValidationError(f"patch references unknown local alias: {endpoint}")
            return aliases[alias]
        return endpoint

    for operation in patch["operations"]:
        if operation["op"] != "add_edge":
            continue
        source = resolve(operation["from"])
        target = resolve(operation["to"])
        if source not in cell_ids or target not in cell_ids:
            raise SchemaValidationError("Decision Patch edge contains a missing Cell")
        expected_edges.add(_build_edge(source, target, operation["relation"], _salt(runtime))["eid"])
    _patch_changed_cells(patch, runtime)
    return expected_edges, superseded_targets


def apply_decision_patch(
    session_dir: PathLike,
    patch: Union[PathLike, Mapping[str, Any]],
    *,
    fault_hook: FaultHook = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Validate and reduce an untrusted typed patch into a new shadow generation."""

    root, runtime = _load_runtime(session_dir)
    current = load_head_projection(session_dir)
    session = _resolve_session(session_dir)
    if _source_manifest(session) != current["source_manifest"]:
        raise RuntimeConflictError("legacy artifacts changed since the committed projection; re-project before applying a patch")
    raw_patch = _load_patch_input(patch)
    candidate = _canonical_patch(
        raw_patch,
        runtime=runtime,
        current_generation=current["generation"],
        allow_stale=True,
    )
    supplied_or_computed = candidate["patch_id"]
    existing_patch_ids = {item.get("patch_id") for item in current["patches"] if isinstance(item, dict)}
    if supplied_or_computed in existing_patch_ids:
        with _writer_lock(root):
            latest_head = _read_head(root)
            if latest_head is None:
                raise RuntimeConflictError("HEAD changed during idempotent patch verification")
            latest = _load_generation(root, runtime, latest_head["generation"])
            if _source_manifest(session) != latest["source_manifest"]:
                raise RuntimeConflictError("legacy artifacts changed during idempotent patch verification")
            latest_patch_ids = {item.get("patch_id") for item in latest["patches"] if isinstance(item, dict)}
            if supplied_or_computed not in latest_patch_ids:
                raise RuntimeConflictError("HEAD no longer contains the idempotent Decision Patch")
            return {
                "ok": True,
                "status": "healthy",
                "generation": latest["generation"],
                "idempotent": True,
                "patch_id": supplied_or_computed,
                "authoritative": False,
            }
    if candidate["base_generation"] != current["generation"]:
        raise RuntimeConflictError("patch base_generation is stale")
    canonical = candidate
    existing_provenance = current["audit_map"].get(canonical["source_ref"])
    if existing_provenance is not None and existing_provenance.get("kind") != "typed-patch":
        raise RuntimeSecurityError("Decision Patch source_ref collides with existing legacy provenance")
    cells = [dict(cell) for cell in current["cells"]]
    edges = [dict(edge) for edge in current["edges"]]
    frontier = [dict(event) for event in current["frontier"]]
    by_id = {cell["cid"]: cell for cell in cells}
    aliases: dict[str, str] = {}
    changed: list[str] = []
    supersessions: list[tuple[str, str]] = []
    superseded_targets = {edge["to"] for edge in edges if edge["relation"] == "supersedes"}
    for operation in canonical["operations"]:
        if operation["op"] not in {"add_cell", "supersede_cell"}:
            continue
        if operation["op"] == "supersede_cell" and operation["target"] not in by_id:
            raise SchemaValidationError("supersede target does not exist")
        if operation["op"] == "supersede_cell" and operation["target"] in superseded_targets:
            raise SchemaValidationError("a Cell may be superseded only once")
        new_cell = _build_cell(operation["cell"], [canonical["source_ref"]], _salt(runtime))
        aliases[operation["local_id"]] = new_cell["cid"]
        changed.append(new_cell["cid"])
        if new_cell["cid"] not in by_id:
            cells.append(new_cell)
            by_id[new_cell["cid"]] = new_cell
            frontier.append(
                {
                    "schema_version": RUNTIME_SCHEMA_VERSION,
                    "seq": len(frontier) + 1,
                    "event": "observed",
                    "fact_key": new_cell["fact_key"],
                    "cell_id": new_cell["cid"],
                    "kind": new_cell["kind"],
                    "state": new_cell["state"],
                    "text": new_cell["text"],
                    "confidence": new_cell["confidence"],
                    "sensitivity": new_cell["sensitivity"],
                    "domains": new_cell["domains"],
                    "risk_flags": new_cell["risk_flags"],
                    "depends_on": [],
                    "source_refs": new_cell["source_refs"],
                }
            )
        if operation["op"] == "supersede_cell":
            supersessions.append((new_cell["cid"], operation["target"]))
            superseded_targets.add(operation["target"])
            changed.append(operation["target"])
            target = by_id[operation["target"]]
            frontier.append(
                {
                    "schema_version": RUNTIME_SCHEMA_VERSION,
                    "seq": len(frontier) + 1,
                    "event": "superseded",
                    "fact_key": target["fact_key"],
                    "cell_id": target["cid"],
                    "kind": target["kind"],
                    "state": "superseded",
                    "text": target["text"],
                    "confidence": target["confidence"],
                    "sensitivity": target["sensitivity"],
                    "domains": target["domains"],
                    "risk_flags": target["risk_flags"],
                    "depends_on": [],
                    "source_refs": target["source_refs"],
                }
            )

    def resolve(value: str) -> str:
        if value.startswith("$"):
            alias = value[1:]
            if alias not in aliases:
                raise SchemaValidationError(f"patch references unknown local alias: {value}")
            return aliases[alias]
        if value not in by_id:
            raise SchemaValidationError(f"patch references unknown cell: {value}")
        return value

    for source, target in supersessions:
        edge = _build_edge(source, target, "supersedes", _salt(runtime))
        if edge["eid"] not in {item["eid"] for item in edges}:
            edges.append(edge)
    for operation in canonical["operations"]:
        if operation["op"] != "add_edge":
            continue
        source = resolve(operation["from"])
        target = resolve(operation["to"])
        changed.extend((source, target))
        edge = _build_edge(source, target, operation["relation"], _salt(runtime))
        if edge["eid"] not in {item["eid"] for item in edges}:
            edges.append(edge)
            if operation["relation"] == "depends_on":
                for event in reversed(frontier):
                    if event["cell_id"] == source and event["event"] == "observed":
                        event["depends_on"] = sorted(set(event["depends_on"] + [target]))
                        break
    _assert_acyclic(edges)
    audit_map = dict(current["audit_map"])
    audit_map.setdefault(canonical["source_ref"], {"kind": "typed-patch", "source_path": "operator-patch.json"})
    projection = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "session_id": runtime["session_id"],
        "cells": sorted(cells, key=lambda item: item["cid"]),
        "edges": sorted(edges, key=lambda item: item["eid"]),
        "frontier": frontier,
        "patches": [*current["patches"], canonical],
        "comparison": {},
        "impact_plan": {"changed_cells": changed},
        "audit_map": audit_map,
        "metrics": {
            **current["metrics"],
            "cell_count": len(cells),
            "edge_count": len(edges),
            "frontier_event_count": len(frontier),
            "patch_count": len(current["patches"]) + 1,
        },
        "source_manifest": current["source_manifest"],
        "session_metadata": current["session_metadata"],
    }
    projection["comparison"] = _comparison(
        projection["cells"],
        frontier,
        projection["edges"],
        current["session_metadata"],
    )
    projection["impact_plan"] = plan_impact(
        projection,
        changed_cells=sorted(set(changed)),
        session_metadata=current["session_metadata"],
    )
    result = commit_projection(
        session_dir,
        projection,
        parent_generation=current["generation"],
        fault_hook=fault_hook,
        now=now,
    )
    result["patch_id"] = canonical["patch_id"]
    result["impact_plan"] = projection["impact_plan"]
    return result


def _permission_problems(root: Path) -> list[dict[str, str]]:
    problems: list[dict[str, str]] = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        if current_path.is_symlink():
            problems.append({"code": "symlink_detected", "path": current_path.relative_to(root).as_posix() or "."})
            directories[:] = []
            continue
        mode = stat.S_IMODE(os.stat(current_path, follow_symlinks=False).st_mode)
        if mode != DIRECTORY_MODE:
            problems.append({"code": "permission_unsafe", "path": current_path.relative_to(root).as_posix() or "."})
        safe_directories: list[str] = []
        for name in directories:
            path = current_path / name
            if path.is_symlink():
                problems.append({"code": "symlink_detected", "path": path.relative_to(root).as_posix()})
            else:
                safe_directories.append(name)
        directories[:] = safe_directories
        for name in files:
            path = current_path / name
            if path.is_symlink():
                problems.append({"code": "symlink_detected", "path": path.relative_to(root).as_posix()})
                continue
            mode = stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)
            if mode != FILE_MODE:
                problems.append({"code": "permission_unsafe", "path": path.relative_to(root).as_posix()})
    return problems


def _generation_directories(root: Path) -> list[Path]:
    directory = root / GENERATIONS_DIR
    if not directory.exists() or directory.is_symlink():
        return []
    return sorted(
        (path for path in directory.iterdir() if GENERATION_RE.fullmatch(path.name)),
        key=lambda path: int(GENERATION_RE.fullmatch(path.name).group(1)),  # type: ignore[union-attr]
    )


def _retention_status(
    root: Path,
    runtime: Mapping[str, Any],
    generations: Mapping[str, Mapping[str, Any]],
    head: Optional[Mapping[str, Any]],
    now: Optional[datetime],
) -> dict[str, Any]:
    retention_days = int(runtime["policy"]["retention_days"])
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    cutoff = current_time.astimezone(timezone.utc) - timedelta(days=retention_days)
    protected: set[str] = set()
    cursor = head.get("generation") if head else None
    while isinstance(cursor, str) and cursor in generations and cursor not in protected:
        protected.add(cursor)
        parent = generations[cursor]["manifest"].get("parent_generation")
        cursor = parent if isinstance(parent, str) else None
    expired_paths: list[str] = []
    for name, generation in generations.items():
        if name in protected:
            continue
        if _parse_timestamp(generation["manifest"]["created_at"]) < cutoff:
            expired_paths.append(f"{GENERATIONS_DIR}/{name}")
    for folder in (STAGING_DIR, QUARANTINE_DIR):
        directory = root / folder
        if not directory.is_dir() or directory.is_symlink():
            continue
        for path in directory.iterdir():
            modified = datetime.fromtimestamp(os.stat(path, follow_symlinks=False).st_mtime, tz=timezone.utc)
            if modified < cutoff:
                expired_paths.append(f"{folder}/{path.name}")
    return {
        "policy": "manual",
        "retention_days": retention_days,
        "automatic_deletion": False,
        "protected_generations": len(protected),
        "expired_candidates": len(expired_paths),
        "expired_paths": sorted(expired_paths),
    }


def doctor_runtime(session_dir: PathLike, *, now: Optional[datetime] = None) -> dict[str, Any]:
    """Read-only runtime health check with explicit fallback state."""

    session = _resolve_session(session_dir)
    root = session / RUNTIME_DIRNAME
    if not root.exists():
        return {
            "ok": True,
            "status": "ignored",
            "fallback_reason": "not_initialized",
            "problems": [],
            "generation": None,
            "retention": {
                "policy": "manual",
                "retention_days": DEFAULT_RETENTION_DAYS,
                "automatic_deletion": False,
                "expired_candidates": 0,
                "expired_paths": [],
            },
            "authoritative": False,
            "read_only": True,
        }
    problems: list[dict[str, str]] = []
    generation: Optional[str] = None
    fallback_reason: Optional[str] = None
    recovery_available = False
    try:
        root, runtime = _load_runtime(session)
    except DecisionRuntimeError as exc:
        message = str(exc)
        code = "permission_unsafe" if "unsafe permissions" in message else "runtime_invalid"
        if "symlink" in message:
            code = "symlink_detected"
        return {
            "ok": False,
            "status": "quarantined",
            "fallback_reason": code,
            "problems": [{"code": code, "message": message}],
            "generation": None,
            "retention": {"policy": "unavailable", "automatic_deletion": False},
            "authoritative": False,
            "read_only": True,
        }
    problems.extend(_permission_problems(root))
    for name in (GENERATIONS_DIR, STAGING_DIR, QUARANTINE_DIR):
        path = root / name
        if path.is_symlink() or not path.is_dir():
            problems.append({"code": "runtime_structure_invalid", "path": name})
    if any(problem["code"] == "runtime_structure_invalid" for problem in problems):
        return {
            "ok": False,
            "status": "quarantined",
            "fallback_reason": "runtime_structure_invalid",
            "problems": problems,
            "generation": None,
            "recovery_available": False,
            "retention": {"policy": "unavailable", "automatic_deletion": False},
            "authoritative": False,
            "read_only": True,
        }
    staging = root / STAGING_DIR
    if staging.is_dir():
        pending = [path for path in staging.iterdir()]
        if pending:
            problems.append({"code": "incomplete_transaction", "path": STAGING_DIR})
            fallback_reason = "incomplete_transaction"
    invalid_generations: list[str] = []
    loaded_generations: dict[str, dict[str, Any]] = {}
    head: Optional[dict[str, Any]] = None
    for path in _generation_directories(root):
        try:
            loaded_generations[path.name] = _load_generation(root, runtime, path.name)
        except DecisionRuntimeError:
            invalid_generations.append(path.name)
    for name in invalid_generations:
        problems.append({"code": "generation_invalid", "path": f"{GENERATIONS_DIR}/{name}"})
    known_generation_names = {path.name for path in _generation_directories(root)}
    for path in (root / GENERATIONS_DIR).iterdir():
        if path.name not in known_generation_names:
            problems.append({"code": "unexpected_generation_entry", "path": f"{GENERATIONS_DIR}/{path.name}"})
    try:
        head = _read_head(root)
        if head is None:
            if loaded_generations:
                problems.append({"code": "head_missing", "path": HEAD_FILE})
                fallback_reason = "head_missing"
                recovery_available = True
            else:
                return {
                    "ok": not problems,
                    "status": "ignored" if not problems else "quarantined",
                    "fallback_reason": "no_committed_generation",
                    "problems": problems,
                    "generation": None,
                    "retention": _retention_status(root, runtime, loaded_generations, head, now),
                    "authoritative": False,
                    "read_only": True,
                }
        else:
            generation = head["generation"]
            current = loaded_generations.get(generation)
            if current is None:
                current = _load_generation(root, runtime, generation)
            if current["manifest_sha256"] != head["manifest_sha256"]:
                raise SchemaValidationError("HEAD manifest checksum mismatch")
            if _source_manifest(session) != current["source_manifest"]:
                problems.append({"code": "legacy_source_changed", "path": "legacy"})
                fallback_reason = "legacy_source_changed"
            if head["reason"] == "commit":
                children = [
                    value
                    for value in loaded_generations.values()
                    if value["manifest"]["parent_generation"] == generation
                ]
                if children:
                    recovery_available = True
                    problems.append({"code": "committed_generation_not_in_head", "path": GENERATIONS_DIR})
                    fallback_reason = "recovery_required"
    except DecisionRuntimeError as exc:
        problems.append({"code": "head_corrupt", "message": str(exc)})
        fallback_reason = "head_corrupt"
        recovery_available = bool(loaded_generations)
    if problems:
        return {
            "ok": False,
            "status": "quarantined",
            "fallback_reason": fallback_reason or problems[0]["code"],
            "problems": problems,
            "generation": generation,
            "recovery_available": recovery_available,
            "retention": _retention_status(root, runtime, loaded_generations, head, now),
            "authoritative": False,
            "read_only": True,
        }
    return {
        "ok": True,
        "status": "recovered" if head and head["reason"] == "recovery" else "healthy",
        "fallback_reason": None,
        "problems": [],
        "generation": generation,
        "recovery_available": False,
        "retention": _retention_status(root, runtime, loaded_generations, head, now),
        "authoritative": False,
        "read_only": True,
    }


def _quarantine_path(root: Path, path: Path, reason: str) -> Optional[Path]:
    if not path.exists() and not path.is_symlink():
        return None
    _assert_confined(path, root)
    safe_reason = re.sub(r"[^a-z0-9-]+", "-", reason.casefold()).strip("-")[:40] or "invalid"
    destination = root / QUARANTINE_DIR / f"{path.name}-{safe_reason}-{uuid.uuid4().hex[:8]}"
    _assert_confined(destination, root)
    os.rename(path, destination)
    _fsync_directory(destination.parent)
    return destination


def recover_runtime(
    session_dir: PathLike,
    *,
    fault_hook: FaultHook = None,
) -> dict[str, Any]:
    """Quarantine incomplete state and recover a unique valid committed chain."""

    session = _resolve_session(session_dir)
    root, runtime = _load_runtime(session)
    with _writer_lock(root):
        quarantined: list[str] = []
        staging = root / STAGING_DIR
        for path in list(staging.iterdir()):
            destination = _quarantine_path(root, path, "incomplete-transaction")
            if destination:
                quarantined.append(destination.name)
        valid: dict[str, dict[str, Any]] = {}
        for path in list(_generation_directories(root)):
            try:
                valid[path.name] = _load_generation(root, runtime, path.name)
            except DecisionRuntimeError:
                destination = _quarantine_path(root, path, "invalid-generation")
                if destination:
                    quarantined.append(destination.name)
        head: Optional[dict[str, Any]]
        try:
            head = _read_head(root)
            if head is not None and head["generation"] not in valid:
                raise SchemaValidationError("HEAD points to an invalid generation")
        except DecisionRuntimeError:
            destination = _quarantine_path(root, _head_path(root), "corrupt-head")
            if destination:
                quarantined.append(destination.name)
            head = None
        selected: Optional[dict[str, Any]] = None
        if head is not None:
            selected = valid[head["generation"]]
            if head["reason"] != "rollback":
                while True:
                    children = [item for item in valid.values() if item["manifest"]["parent_generation"] == selected["generation"]]
                    if not children:
                        break
                    if len(children) != 1:
                        raise RuntimeConflictError("recovery found ambiguous committed branches")
                    selected = children[0]
        elif valid:
            roots = [item for item in valid.values() if item["manifest"]["parent_generation"] is None]
            if len(roots) != 1:
                raise RuntimeConflictError("recovery cannot identify a unique root generation")
            selected = roots[0]
            while True:
                children = [item for item in valid.values() if item["manifest"]["parent_generation"] == selected["generation"]]
                if not children:
                    break
                if len(children) != 1:
                    raise RuntimeConflictError("recovery found ambiguous committed branches")
                selected = children[0]
        if selected is None:
            return {
                "ok": True,
                "status": "ignored",
                "fallback_reason": "no_committed_generation",
                "generation": None,
                "quarantined": quarantined,
                "authoritative": False,
            }
        if _source_manifest(session) != selected["source_manifest"]:
            raise RuntimeConflictError("legacy artifacts changed; recovery cannot activate a stale shadow generation")
        _fault(fault_hook, "before_recovery_head")
        _write_head(root, selected["generation"], selected["manifest_sha256"], "recovery", fault_hook)
        return {
            "ok": True,
            "status": "recovered",
            "generation": selected["generation"],
            "quarantined": quarantined,
            "authoritative": False,
        }


def rollback_runtime(
    session_dir: PathLike,
    generation_id: str,
    *,
    fault_hook: FaultHook = None,
) -> dict[str, Any]:
    """Move HEAD to a verified ancestor without deleting evidence."""

    session = _resolve_session(session_dir)
    root, runtime = _load_runtime(session)
    if not GENERATION_RE.fullmatch(generation_id):
        raise SchemaValidationError("invalid rollback generation")
    with _writer_lock(root):
        head = _read_head(root)
        if head is None:
            raise RuntimeNotInitialized("cannot rollback without HEAD")
        current = _load_generation(root, runtime, head["generation"])
        ancestors: set[str] = set()
        cursor: Optional[dict[str, Any]] = current
        while cursor is not None:
            ancestors.add(cursor["generation"])
            parent = cursor["manifest"]["parent_generation"]
            cursor = _load_generation(root, runtime, parent) if parent is not None else None
        if generation_id not in ancestors:
            raise RuntimeConflictError("rollback target is not an ancestor of HEAD")
        target = _load_generation(root, runtime, generation_id)
        if _source_manifest(session) != target["source_manifest"]:
            raise RuntimeConflictError("legacy artifacts changed; rollback cannot activate a stale shadow generation")
        _write_head(root, generation_id, target["manifest_sha256"], "rollback", fault_hook)
        return {
            "ok": True,
            "status": "healthy",
            "generation": generation_id,
            "previous_generation": head["generation"],
            "evidence_deleted": False,
            "authoritative": False,
        }


def _secure_remove(path: Path, root: Path, *, allow_root: bool = False) -> None:
    _assert_confined(path, root.parent if allow_root else root)
    if path.is_symlink():
        path.unlink()
        return
    if path.is_dir():
        for entry in os.scandir(path):
            child = Path(entry.path)
            if entry.is_symlink():
                child.unlink()
            elif entry.is_dir(follow_symlinks=False):
                _secure_remove(child, root)
            else:
                child.unlink()
        path.rmdir()
    elif path.exists():
        path.unlink()


def purge_runtime(
    session_dir: PathLike,
    *,
    expired: bool = False,
    all_runtime: bool = False,
    confirm: Optional[str] = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Explicitly purge expired non-HEAD state or the whole optional sidecar."""

    session = _resolve_session(session_dir)
    root = session / RUNTIME_DIRNAME
    if not root.exists():
        return {"ok": True, "status": "ignored", "removed": [], "authoritative": False}
    root, runtime = _load_runtime(session)
    if all_runtime:
        if confirm != session.name:
            raise RuntimeSecurityError("full purge requires confirm equal to the session id")
        tombstone = session / f".{RUNTIME_DIRNAME}-purge-{uuid.uuid4().hex}"
        with _writer_lock(root):
            if not root.exists() or root.is_symlink():
                raise RuntimeConflictError("runtime changed while preparing full purge")
            os.rename(root, tombstone)
            _fsync_directory(session)
        _secure_remove(tombstone, tombstone, allow_root=True)
        _fsync_directory(session)
        return {
            "ok": True,
            "status": "ignored",
            "removed": [RUNTIME_DIRNAME],
            "legacy_deleted": False,
            "authoritative": False,
        }
    if not expired:
        raise ValueError("purge requires expired=True or all_runtime=True")
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    cutoff = current_time.astimezone(timezone.utc) - timedelta(days=retention_days)
    removed: list[str] = []
    with _writer_lock(root):
        head = _read_head(root)
        ancestors: set[str] = set()
        if head is not None:
            cursor: Optional[dict[str, Any]] = _load_generation(root, runtime, head["generation"])
            while cursor is not None:
                ancestors.add(cursor["generation"])
                parent = cursor["manifest"]["parent_generation"]
                cursor = _load_generation(root, runtime, parent) if parent is not None else None
        for path in list(_generation_directories(root)):
            if path.name in ancestors:
                continue
            try:
                generation = _load_generation(root, runtime, path.name)
                created = _parse_timestamp(generation["manifest"]["created_at"])
            except DecisionRuntimeError:
                created = datetime.fromtimestamp(os.stat(path, follow_symlinks=False).st_mtime, tz=timezone.utc)
            if created < cutoff:
                _secure_remove(path, root)
                removed.append(f"{GENERATIONS_DIR}/{path.name}")
        for folder in (STAGING_DIR, QUARANTINE_DIR):
            directory = root / folder
            for path in list(directory.iterdir()):
                modified = datetime.fromtimestamp(os.stat(path, follow_symlinks=False).st_mtime, tz=timezone.utc)
                if modified < cutoff:
                    _secure_remove(path, root)
                    removed.append(f"{folder}/{path.name}")
        _fsync_directory(root)
    return {
        "ok": True,
        "status": doctor_runtime(session)["status"],
        "removed": sorted(removed),
        "legacy_deleted": False,
        "automatic": False,
        "authoritative": False,
    }


def _corpus_case_paths(corpus: Path) -> list[Path]:
    if not corpus.is_dir():
        raise NotADirectoryError(str(corpus))
    manifest_path = corpus / "manifest.json"
    if manifest_path.exists():
        manifest = strict_json_loads(manifest_path.read_text(encoding="utf-8"), max_bytes=MAX_SOURCE_BYTES)
        if not isinstance(manifest, dict):
            raise SchemaValidationError("corpus manifest must be an object")
        _unknown_fields(manifest, {"schema_version", "cases"}, "corpus manifest")
        _require_fields(manifest, {"schema_version", "cases"}, "corpus manifest")
        if manifest["schema_version"] != RUNTIME_SCHEMA_VERSION or not isinstance(manifest["cases"], list):
            raise SchemaValidationError("invalid corpus manifest")
        paths: list[Path] = []
        for name in manifest["cases"]:
            if not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts:
                raise RuntimeSecurityError("invalid corpus case path")
            path = corpus / name
            if path.is_symlink() or not path.is_file():
                raise RuntimeSecurityError(f"unsafe corpus case: {name}")
            paths.append(path)
        return paths
    return sorted(path for path in corpus.glob("case-*.json") if path.is_file() and not path.is_symlink())


def _load_corpus_case(path: Path) -> dict[str, Any]:
    value = strict_json_loads(path.read_text(encoding="utf-8"), max_bytes=MAX_SOURCE_BYTES)
    if not isinstance(value, dict):
        raise SchemaValidationError("corpus case must be an object")
    _unknown_fields(value, {"schema_version", "name", "session", "artifacts", "expected"}, "corpus case")
    _require_fields(value, {"schema_version", "name", "session", "artifacts", "expected"}, "corpus case")
    if value["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise SchemaValidationError("unknown corpus case schema")
    if not isinstance(value["name"], str) or not value["name"].strip():
        raise SchemaValidationError("corpus case name must be non-empty")
    if not isinstance(value["session"], dict) or not isinstance(value["artifacts"], dict) or not isinstance(value["expected"], dict):
        raise SchemaValidationError("corpus session/artifacts/expected must be objects")
    _unknown_fields(value["session"], {"topic", "mode", "session_type", "risk_flags", "frontend_review"}, "corpus session")
    _unknown_fields(value["expected"], {"blockers", "dissent", "verification", "forced_full"}, "corpus expected")
    return value


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.casefold())).strip("-")[:48] or "case"


def _materialize_case(case: Mapping[str, Any], base: Path) -> Path:
    session = base / f"fixture-{_slug(str(case['name']))}"
    session.mkdir(mode=DIRECTORY_MODE)
    session_data = {
        "topic": case["session"].get("topic", case["name"]),
        "mode": case["session"].get("mode", "standard"),
        "session_type": case["session"].get("session_type", "general"),
        "activation_tags": ["frontend-ui-ux"] if case["session"].get("frontend_review") else [],
        "route_decision": {"risk_flags": case["session"].get("risk_flags", [])},
    }
    (session / "session.json").write_text(json.dumps(session_data, sort_keys=True) + "\n", encoding="utf-8")
    for relative, content in case["artifacts"].items():
        if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise RuntimeSecurityError("corpus artifact path escapes session")
        path = session / relative
        allowed = relative in {"final.md", "decision-ledger.json", "findings.jsonl"} or (
            len(Path(relative).parts) == 2
            and Path(relative).parts[0] in {"members", "reviews"}
            and Path(relative).suffix == ".md"
        )
        if not allowed:
            raise RuntimeSecurityError(f"corpus artifact is not allowlisted: {relative}")
        path.parent.mkdir(mode=DIRECTORY_MODE, parents=True, exist_ok=True)
        rendered = json.dumps(content, sort_keys=True, indent=2) + "\n" if isinstance(content, (dict, list)) else str(content)
        path.write_text(rendered, encoding="utf-8")
    return session


def _semantic_replay_digest(projection: Mapping[str, Any]) -> str:
    value = {
        "cells": projection["cells"],
        "edges": projection["edges"],
        "frontier": projection["frontier"],
        "comparison": projection["comparison"],
        "impact_plan": projection["impact_plan"],
    }
    return _sha256(canonical_json(value).encode("utf-8"))


def _case_counts(projection: Mapping[str, Any]) -> dict[str, int]:
    counts = {"blockers": 0, "dissent": 0, "verification": 0}
    for cell in projection["cells"]:
        if cell["kind"] == "blocker":
            counts["blockers"] += 1
        elif cell["kind"] == "dissent":
            counts["dissent"] += 1
        elif cell["kind"] == "verification":
            counts["verification"] += 1
    return counts


def replay_corpus(
    corpus: PathLike,
    *,
    repetitions: int = 10,
    compare: str = "frontier",
) -> dict[str, Any]:
    """Replay a sanitized fixture corpus and verify deterministic semantics."""

    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    corpus_path = Path(corpus).expanduser().resolve(strict=True)
    case_paths = _corpus_case_paths(corpus_path)
    if not case_paths:
        raise DecisionRuntimeError("corpus contains no cases")
    results: list[dict[str, Any]] = []
    all_ok = True
    for case_path in case_paths:
        case = _load_corpus_case(case_path)
        digests: list[str] = []
        observed_counts: Optional[dict[str, int]] = None
        forced_full: Optional[bool] = None
        for _ in range(repetitions):
            with tempfile.TemporaryDirectory() as temporary:
                session = _materialize_case(case, Path(temporary))
                deterministic_salt = hashlib.sha256(str(case["name"]).encode("utf-8")).hexdigest()
                _initialize_runtime(session, salt_hex=deterministic_salt, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
                project_session(session, compare=compare, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
                projection = load_head_projection(session)
                digests.append(_semantic_replay_digest(projection))
                observed_counts = _case_counts(projection)
                forced_full = bool(projection["impact_plan"]["forced_full"])
        expected = case["expected"]
        expected_counts = {key: expected.get(key, 0) for key in ("blockers", "dissent", "verification")}
        deterministic = len(set(digests)) == 1
        counts_match = observed_counts == expected_counts
        plan_match = forced_full == bool(expected.get("forced_full", True))
        case_ok = deterministic and counts_match and plan_match
        all_ok = all_ok and case_ok
        results.append(
            {
                "name": case["name"],
                "ok": case_ok,
                "deterministic": deterministic,
                "digest": digests[0],
                "counts": observed_counts,
                "expected_counts": expected_counts,
                "forced_full": forced_full,
            }
        )
    return {
        "ok": all_ok,
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "case_count": len(results),
        "repetitions": repetitions,
        "compare": compare,
        "cases": results,
        "authoritative": False,
    }


FAULT_POINTS = (
    "after_prepared",
    "after_write_cells_jsonl",
    "after_write_edges_jsonl",
    "after_write_patches_jsonl",
    "after_write_frontier_jsonl",
    "after_write_comparison_json",
    "after_write_impact_plan_json",
    "after_write_audit_map_json",
    "after_write_metrics_json",
    "after_manifest",
    "after_validated",
    "after_generation_rename",
    "after_committed",
    "before_head_replace",
    "after_head_replace",
)


def fault_test_corpus(corpus: PathLike) -> dict[str, Any]:
    """Exercise every durable phase and prove HEAD is always old-or-new valid."""

    corpus_path = Path(corpus).expanduser().resolve(strict=True)
    paths = _corpus_case_paths(corpus_path)
    if not paths:
        raise DecisionRuntimeError("corpus contains no cases")
    case = _load_corpus_case(paths[0])
    results: list[dict[str, Any]] = []
    for point in FAULT_POINTS:
        with tempfile.TemporaryDirectory() as temporary:
            session = _materialize_case(case, Path(temporary))
            salt_hex = hashlib.sha256(str(case["name"]).encode("utf-8")).hexdigest()
            _initialize_runtime(session, salt_hex=salt_hex, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
            project_session(session, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
            baseline = load_head_projection(session)
            legacy_before = _source_manifest(session)
            patch = {
                "schema_version": RUNTIME_SCHEMA_VERSION,
                "session_id": session.name,
                "base_generation": baseline["generation"],
                "source_ref": "operator",
                "operations": [
                    {
                        "op": "add_cell",
                        "local_id": "faultProbe",
                        "cell": {
                            "kind": "claim",
                            "state": "open",
                            "text": "Deterministic transaction fault probe",
                            "confidence": "unknown",
                            "sensitivity": "internal",
                            "domains": ["testing"],
                            "risk_flags": [],
                        },
                    }
                ],
            }

            def inject(candidate: str, expected: str = point) -> None:
                if candidate == expected:
                    raise InjectedFault(expected)

            injected = False
            try:
                apply_decision_patch(session, patch, fault_hook=inject, now=datetime(2026, 1, 2, tzinfo=timezone.utc))
            except InjectedFault:
                injected = True
            health_before = doctor_runtime(session)
            if not health_before["ok"]:
                try:
                    recover_runtime(session)
                except DecisionRuntimeError:
                    pass
            health_after = doctor_runtime(session)
            try:
                loaded = load_head_projection(session)
                head_valid = loaded["generation"] in {baseline["generation"], *[path.name for path in _generation_directories(runtime_root(session))]}
            except DecisionRuntimeError:
                head_valid = False
            legacy_unchanged = legacy_before == _source_manifest(session)
            ok = injected and head_valid and legacy_unchanged and health_after["ok"]
            results.append(
                {
                    "point": point,
                    "ok": ok,
                    "injected": injected,
                    "head_valid": head_valid,
                    "legacy_unchanged": legacy_unchanged,
                    "observed_status": health_before["status"],
                    "final_status": health_after["status"],
                }
            )
    return {
        "ok": all(item["ok"] for item in results),
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "points": results,
        "authoritative": False,
    }


__all__ = [
    "DecisionRuntimeError",
    "SchemaValidationError",
    "RuntimeSecurityError",
    "RuntimeLockError",
    "RuntimeConflictError",
    "RuntimeNotInitialized",
    "PrivacyViolation",
    "InjectedFault",
    "runtime_root",
    "project_session",
    "commit_projection",
    "load_head_projection",
    "apply_decision_patch",
    "plan_impact",
    "doctor_runtime",
    "recover_runtime",
    "rollback_runtime",
    "purge_runtime",
    "replay_corpus",
    "fault_test_corpus",
]
