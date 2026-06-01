from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from pages.components.shared import (
    _collect_folder_materials,
    _collect_zip_materials,
    _safe_zip_member_name,
)


class UploadDouble:
    def __init__(self, name: str, payload: bytes) -> None:
        self.name = name
        self._payload = payload

    def getvalue(self) -> bytes:
        return self._payload


def test_collect_folder_materials_reads_supported_files_recursively(tmp_path) -> None:
    root = tmp_path / "context"
    nested = root / "docs"
    nested.mkdir(parents=True)
    (root / "brief.txt").write_text("核心问题", encoding="utf-8")
    (nested / "metrics.csv").write_text("day,revenue\n1,100\n2,150\n", encoding="utf-8")
    (nested / "image.png").write_bytes(b"not parsed")

    materials = _collect_folder_materials(root)

    assert [item["name"] for item in materials] == ["brief.txt", "docs/metrics.csv"]
    assert "核心问题" in materials[0]["text"]
    assert "CSV rows: 2" in materials[1]["text"]


def test_collect_zip_materials_ignores_unsafe_and_unsupported_entries(tmp_path) -> None:
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("folder/input.md", "参考材料")
        archive.writestr("../escape.txt", "bad")
        archive.writestr("__MACOSX/hidden.txt", "bad")
        archive.writestr("folder/image.png", "bad")

    upload = UploadDouble("context.zip", payload.getvalue())

    materials = _collect_zip_materials(upload, tmp_path)

    assert [item["name"] for item in materials] == ["folder/input.md"]
    assert materials[0]["text"] == "参考材料"


def test_safe_zip_member_name_rejects_path_traversal() -> None:
    assert _safe_zip_member_name("../secret.txt") is None
    assert _safe_zip_member_name("/absolute.txt") is None
    assert _safe_zip_member_name("safe/input.txt").as_posix() == "safe/input.txt"
