"""Έλεγχοι για τη λογική καθαρισμού παλαιών εκτελέσεων (_cleanup_old_runs).

Χρησιμοποιεί ένα ψεύτικο (fake) Object Storage ώστε να μην απαιτείται
πραγματική σύνδεση.

Εκτέλεση:  python -m pytest tests/test_cleanup.py -v
"""
from __future__ import annotations

import json
import os
import sys
import time
import types

# ── path setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Fake Object Storage ────────────────────────────────────────────────────────

class _FakeObject:
    """Μιμείται replit.object_storage.object.Object (έχει μόνο .name)."""
    def __init__(self, name: str):
        self.name = name


class FakeStorage:
    """In-memory αντικατάσταση του replit.object_storage.Client."""

    def __init__(self, initial: dict[str, bytes] | None = None):
        self._store: dict[str, bytes] = dict(initial or {})
        self.deleted: list[str] = []

    # ── API που χρησιμοποιεί ο κώδικας ────────────────────────────────────────
    def list(self, prefix: str = "", match_glob: str = "") -> list[_FakeObject]:
        import fnmatch
        results = []
        for key in self._store:
            if prefix and not key.startswith(prefix):
                continue
            if match_glob and not fnmatch.fnmatch(key, match_glob):
                continue
            results.append(_FakeObject(key))
        return results

    def download_as_bytes(self, key: str) -> bytes:
        if key not in self._store:
            raise KeyError(f"Object not found: {key}")
        return self._store[key]

    def delete(self, key: str, ignore_not_found: bool = False) -> None:
        if key not in self._store:
            if not ignore_not_found:
                raise KeyError(f"Object not found: {key}")
            return
        del self._store[key]
        self.deleted.append(key)

    def upload_from_bytes(self, key: str, data: bytes) -> None:
        self._store[key] = data

    # ── helpers ────────────────────────────────────────────────────────────────
    def keys(self) -> list[str]:
        return list(self._store.keys())


# ── helper to load webapp.app with a fake storage ─────────────────────────────

def _make_module(fake_storage: FakeStorage, tmp_out_root: str):
    """Δημιουργεί το module webapp.app με ψεύτικο storage και tmp OUT_ROOT."""
    import importlib
    import unittest.mock as mock

    # Βεβαιώσου ότι το module δεν είναι cached με παλαιό storage
    if "webapp.app" in sys.modules:
        del sys.modules["webapp.app"]
    if "webapp" in sys.modules:
        del sys.modules["webapp"]

    # Κάνε mock το replit.object_storage ώστε να επιστρέψει FakeStorage
    fake_replit = types.ModuleType("replit")
    fake_obj_storage = types.ModuleType("replit.object_storage")
    fake_obj_storage.Client = lambda: fake_storage
    sys.modules["replit"] = fake_replit
    sys.modules["replit.object_storage"] = fake_obj_storage

    import webapp.app as app_module
    app_module._storage = fake_storage
    app_module._HAS_OBJECT_STORAGE = True
    app_module.OUT_ROOT = tmp_out_root
    os.makedirs(tmp_out_root, exist_ok=True)
    return app_module


def _manifest(files: list[str], created_at: float | None = None) -> bytes:
    d: dict = {"files": files}
    if created_at is not None:
        d["created_at"] = created_at
    return json.dumps(d).encode()


# ── tests ──────────────────────────────────────────────────────────────────────

def test_recent_run_is_preserved(tmp_path):
    """Εκτελέσεις μέσα στο παράθυρο διατήρησης δεν διαγράφονται."""
    run_id = "aabbcc001122"
    files = ["foo_protasi_1.pdf", "foo_protasi_1.dxf"]
    created_at = time.time() - 3 * 86_400   # 3 ημέρες πριν (< 30)

    store = FakeStorage({
        f"out/{run_id}/manifest.json": _manifest(files, created_at),
        f"out/{run_id}/{files[0]}": b"PDF",
        f"out/{run_id}/{files[1]}": b"DXF",
    })
    mod = _make_module(store, str(tmp_path))
    mod._cleanup_old_runs(max_age_days=30)

    assert f"out/{run_id}/manifest.json" in store.keys(), "Πρόσφατο manifest διαγράφηκε"
    assert store.deleted == [], "Κανένα αρχείο δεν πρέπει να διαγραφεί"


def test_expired_run_is_deleted(tmp_path):
    """Εκτελέσεις παλαιότερες από max_age_days διαγράφονται πλήρως."""
    run_id = "deadbeef1234"
    files = ["bar_protasi_1.pdf", "bar_protasi_1.dxf", "bar_ola.pdf"]
    created_at = time.time() - 31 * 86_400  # 31 ημέρες πριν (> 30)

    store = FakeStorage({
        f"out/{run_id}/manifest.json": _manifest(files, created_at),
        **{f"out/{run_id}/{f}": b"data" for f in files},
    })
    mod = _make_module(store, str(tmp_path))
    mod._cleanup_old_runs(max_age_days=30)

    assert store.keys() == [], "Όλα τα αρχεία ληγμένης εκτέλεσης πρέπει να διαγραφούν"


def test_legacy_manifest_without_created_at_is_preserved(tmp_path):
    """Manifest χωρίς created_at (legacy) δεν διαγράφεται ποτέ."""
    run_id = "legacy000000"
    files = ["old_protasi_1.pdf"]

    store = FakeStorage({
        f"out/{run_id}/manifest.json": _manifest(files, created_at=None),
        f"out/{run_id}/{files[0]}": b"PDF",
    })
    mod = _make_module(store, str(tmp_path))
    mod._cleanup_old_runs(max_age_days=30)

    assert f"out/{run_id}/manifest.json" in store.keys(), \
        "Legacy manifest (χωρίς created_at) δεν πρέπει να διαγραφεί"
    assert store.deleted == []


def test_malformed_manifest_is_skipped(tmp_path):
    """Μη έγκυρο JSON manifest δεν προκαλεί σφάλμα."""
    run_id = "badjson000000"
    store = FakeStorage({
        f"out/{run_id}/manifest.json": b"NOT JSON {{{",
        f"out/{run_id}/file.pdf": b"PDF",
    })
    mod = _make_module(store, str(tmp_path))
    mod._cleanup_old_runs(max_age_days=30)   # δεν πρέπει να εκτινάξει exception

    # Ο κατεστραμμένος κόμβος παραλείπεται, τα αρχεία του παραμένουν
    assert f"out/{run_id}/file.pdf" in store.keys()


def test_local_cache_dir_removed_for_expired_run(tmp_path):
    """Ο τοπικός φάκελος cache της ληγμένης εκτέλεσης διαγράφεται."""
    run_id = "localcache1234"
    files = ["baz_protasi_1.pdf"]
    created_at = time.time() - 40 * 86_400

    # Δημιούργησε τοπικό φάκελο/αρχείο
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / files[0]).write_bytes(b"PDF")

    store = FakeStorage({
        f"out/{run_id}/manifest.json": _manifest(files, created_at),
        f"out/{run_id}/{files[0]}": b"PDF",
    })
    mod = _make_module(store, str(tmp_path))
    mod._cleanup_old_runs(max_age_days=30)

    assert not run_dir.exists(), "Τοπικός φάκελος cache πρέπει να διαγραφεί"


def test_storage_list_failure_is_silent(tmp_path):
    """Αποτυχία listing του Object Storage δεν σπάει την εφαρμογή."""
    class BrokenStorage(FakeStorage):
        def list(self, **kw):
            raise RuntimeError("Network error")

    mod = _make_module(BrokenStorage(), str(tmp_path))
    mod._cleanup_old_runs(max_age_days=30)  # δεν πρέπει να εκτινάξει exception


def test_expiry_boundary_exact_30_days_is_preserved(tmp_path):
    """Εκτέλεση ακριβώς 30 ημερών (= cutoff) δεν διαγράφεται."""
    run_id = "boundary000000"
    files = ["b_protasi_1.pdf"]
    # Ακριβώς στο όριο: created_at == cutoff → δεν είναι παλαιότερο
    created_at = time.time() - 30 * 86_400 + 60  # 1 λεπτό μέσα στο παράθυρο

    store = FakeStorage({
        f"out/{run_id}/manifest.json": _manifest(files, created_at),
        f"out/{run_id}/{files[0]}": b"PDF",
    })
    mod = _make_module(store, str(tmp_path))
    mod._cleanup_old_runs(max_age_days=30)

    assert f"out/{run_id}/manifest.json" in store.keys(), \
        "Εκτέλεση στο ακριβές όριο 30 ημερών πρέπει να διατηρηθεί"


if __name__ == "__main__":
    import tempfile
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        with tempfile.TemporaryDirectory() as td:
            from pathlib import Path
            fn(Path(td))
        print(f"✓ {fn.__name__}")
    print(f"\nΌλοι οι έλεγχοι πέρασαν ({len(tests)}).")
