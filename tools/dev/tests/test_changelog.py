import json
from pathlib import Path


schema_diff = Path(__file__).parent.parent / "changelog.py"
with open(schema_diff, encoding='utf-8') as f:
    exec(f.read())


def test_schema_diff():
    data_dir = Path(__file__).parent / "data"
    with open(data_dir / "schema-old.json") as f:
        schema_old = json.load(f)
    with open(data_dir / "schema-new.json") as f:
        schema_new = json.load(f)
    with open(data_dir / "diff.md", encoding='utf-8') as f:
        expected = f.read()

    result = schema_diff(schema_old, schema_new)  # noqa
    assert result == expected
