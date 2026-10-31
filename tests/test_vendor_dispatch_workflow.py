"""Parent vendor dispatch in CI stays a verify of vendor.lock.json."""
import re
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".github/workflows").is_dir())
WORKFLOW = ROOT / ".github/workflows/ci.yml"
AT = chr(64)

ACTION_PINS = {
    "actions/setup-node": "949feb2413d6458794dcd2491c4babbbce0c15c1",
    "actions/setup-python": "6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "astral-sh/setup-uv": "68559e99cc807c1eb7e9238fd43a15bba460eec2",
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/upload-artifact": "cf430e030ddbb5b0abf93d22962f4752f3646cd9",
}


def _uses_lines(text):
    return [
        line.strip()
        for line in text.splitlines()
        if re.match(r"(?:-\s+)?uses:", line.strip())
    ]


def test_all_actions_are_pinned_to_full_shas():
    lines = _uses_lines(WORKFLOW.read_text(encoding="utf-8"))
    assert lines
    assert any(line.startswith("uses:") for line in lines)
    for line in lines:
        match = re.search(re.escape(AT) + r"([0-9a-f]{40})\s+#\s+v\d+\.\d+\.\d+\s*$", line)
        assert match, line
        owner = line.split(AT, 1)[0].split()[-1]
        assert match.group(1) == ACTION_PINS[owner], line


def test_vendor_dispatch_verifies_the_lock_without_record():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pilot/vendor_dispatch.py" in text
    assert "vendor.lock.json" in text
    assert 'PARENT_REPOSITORY_ID: "638801160"' in text
    assert "git ls-remote" in text
    assert "refs/heads/main" in text
    invocations = [
        line for line in text.splitlines()
        if "vendor_dispatch.py" in line and not line.lstrip().startswith("#")
    ]
    assert invocations
    for line in invocations:
        assert "--record" not in line
        assert "-S" not in line
    assert (ROOT / "vendor.lock.json").is_file()
