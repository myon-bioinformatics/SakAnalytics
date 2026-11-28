"""Source provenance checks for saved Aoi evidence."""
import hashlib
import json
import os
from pathlib import Path
import warnings

import aoi_paths

ROOT = aoi_paths.resolve_aoi_root(anchor=Path(__file__))
CYCLE = aoi_paths.resolve_cycle_path(ROOT)


def aoi_copy(rel):
    """Aoi の中の実体。Aoi が取り込んだ後は sakanalytics/<フォルダ>/、取り込む前は sakanalytics/ 直下。"""
    moved = ROOT / 'sakanalytics' / rel
    return moved if moved.is_file() else ROOT / 'sakanalytics' / Path(rel).name


def verify_source_sha(out, artifact, field, recorded, source, *, report_only=False):
    """記録の生成元ハッシュを確かめる。記録は書き換えない（自動で基準を更新しない）。

    今のファイルが記録と同じなら、それで終わり。違うなら、source-divergence.json に
    その差（記録時のハッシュ → 今のハッシュ、生成物は作り直していない）が書いてあることを求める。
    pull_request の CI は SOURCE_HASH_CHECK=report を渡し、不一致を警告にする。
    """
    current = hashlib.sha256(source.read_bytes()).hexdigest()
    path = out / 'source-divergence.json'
    rows = json.loads(path.read_text(encoding='utf-8'))['source_divergence'] if path.exists() else []
    rel = source.relative_to(ROOT).as_posix()
    matching = [r for r in rows if r['path'] == rel and r['field'] == field]
    problems = []
    if len(matching) > 1:
        problems.append(f'{rel}: multiple source-divergence rows for {field}')
    elif current == recorded:
        if matching:
            problems.append(f'{rel}: divergence recorded but the file matches the evidence')
    elif not matching:
        problems.append(
            f'{rel}: SHA-256 drift in {artifact} {field}; review provenance, never auto-rebaseline')
    else:
        row = matching[0]
        if row['evidence_sha256'] != recorded or row['current_sha256'] != current:
            problems.append(f'{rel}: source-divergence row does not match {artifact} {field}')
        if row['artifacts_regenerated'] is not False or row['inputs_regenerated'] is not False:
            problems.append(f'{rel}: source-divergence must keep artifacts_regenerated and inputs_regenerated false')
        reason = row['reason']
        if not isinstance(reason, str) or not reason.strip():
            problems.append(f'{rel}: source-divergence reason is empty')
    if problems:
        message = '\n'.join(problems)
        if not report_only:
            raise AssertionError(message)
        warnings.warn(message, UserWarning, stacklevel=2)
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            print('::warning::' + ' '.join(message.split()))
