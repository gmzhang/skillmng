"""zip 导入安全测试 (PRD §17.2.1)。"""
from __future__ import annotations

import io
import zipfile

import pytest


def _make_zip(files: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, content in files.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            zf.writestr(path, data)
    return buf.getvalue()


GOOD_SKILL_MD = """---
name: imported-skill
description: 导入测试 Skill,触发关键词:import demo,使用场景:zip 导入。
---

# imported-skill

正文。
"""


def _make_md(name: str) -> str:
    return GOOD_SKILL_MD.replace("imported-skill", name)


def _upload(client, name: str, data: bytes):
    return client.post(
        "/api/import/zip",
        files={"file": (name, data, "application/zip")},
    )


def test_good_zip_imports(alice_client):
    data = _make_zip(
        {
            "SKILL.md": _make_md("good-zip"),
            "scripts/run.sh": "#!/usr/bin/env bash\necho ok\n",
        }
    )
    resp = _upload(alice_client, "good.zip", data)
    assert resp.status_code == 201, resp.text
    sid = resp.json()["skill_id"]

    listing = alice_client.get(f"/api/skills/{sid}/files").json()
    paths = {f["path"] for f in listing}
    assert "SKILL.md" in paths
    assert "scripts/run.sh" in paths


def test_zip_with_dotdot_rejected(alice_client):
    data = _make_zip(
        {
            "SKILL.md": _make_md("zip-dotdot"),
            "../evil.txt": "boom",
        }
    )
    resp = _upload(alice_client, "evil.zip", data)
    assert resp.status_code in (400, 422), resp.text


@pytest.mark.parametrize("bad_path", ["/etc/passwd", "..\\evil.txt", "\\absolute.txt"])
def test_zip_absolute_or_traversal_rejected(alice_client, bad_path: str):
    data = _make_zip(
        {
            "SKILL.md": _make_md("zip-bad-path"),
            bad_path: "x",
        }
    )
    resp = _upload(alice_client, "bad.zip", data)
    assert resp.status_code in (400, 422)


def test_zip_missing_skill_md_rejected(alice_client):
    data = _make_zip({"scripts/run.sh": "x"})
    resp = _upload(alice_client, "no-md.zip", data)
    assert resp.status_code in (400, 422)


def test_zip_bad_skill_md_rejected(alice_client):
    data = _make_zip({"SKILL.md": "no frontmatter here"})
    resp = _upload(alice_client, "bad-md.zip", data)
    assert resp.status_code in (400, 422)


def test_import_skill_md_text(alice_client):
    resp = alice_client.post(
        "/api/import/skill-md", json={"content": _make_md("md-text-only")}
    )
    assert resp.status_code == 201


def test_export_round_trip(alice_client):
    data = _make_zip({"SKILL.md": _make_md("round-trip-zip"), "ref.md": "ref"})
    sid = _upload(alice_client, "rt.zip", data).json()["skill_id"]
    resp = alice_client.get(f"/api/skills/{sid}/export.zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    # 二次打开
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = set(zf.namelist())
        assert "SKILL.md" in names
        assert "ref.md" in names
