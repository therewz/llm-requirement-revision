"""Build a derivative dataset and matched packets from hash-pinned original inputs."""

from copy import deepcopy
import csv
import difflib
import hashlib
import json
from pathlib import Path

from . import task_a, task_b

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'runs/cleaned_starts_v1'
ORIGINAL = ROOT / 'runs/withdrawal_keys_v1'
PACKETS = ROOT / 'runs/matched_inputs_v2'
SELECTION = ROOT / 'runs/protocol_freeze_v1/selected_config.json'
SELECTION_HASH = '211d0ab082a81ab11ae133e72bb70a65fe42456f4e5cf24aeb6f2a1d2e15a5d3'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()


def write_same(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and path.read_bytes() != data):
        raise ValueError(f'Refusing to replace a different artifact: {path}')
    if not path.exists():
        with path.open('xb') as handle:
            handle.write(data)


def read_checked(path, sha256):
    data = path.read_bytes()
    if digest(data) != sha256:
        raise ValueError(f'Changed input: {path}')
    return data


def artifact(path, data):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(data), 'bytes': len(data)}


def parent():
    selection = json.loads(read_checked(SELECTION, SELECTION_HASH))
    hashes = {row['path']: row['sha256'] for row in selection['bindings']}
    for path, sha256 in hashes.items():
        read_checked(ROOT / path, sha256)
    return selection


def build():
    selection = parent()
    manifest = json.loads((PACKETS / 'build_manifest.json').read_bytes())
    inventory = {r['participant_id']: r for r in json.loads((ORIGINAL / 'inventory.json').read_bytes())}
    with (ORIGINAL / 'derived/programs.csv').open() as stream:
        profiles = {r['participant_id']: r['selected_profile'] for r in csv.DictReader(stream)}
    if len(inventory) != 72 or {r['participant_id'] for r in manifest['records']} != set(inventory):
        raise ValueError('Frozen inputs do not cover the same 72 participants')
    records = {}
    for row in manifest['records']:
        sid, task, group = (row[key] for key in ('participant_id', 'task', 'group'))
        original = inventory[sid]['P2']
        source = read_checked(ROOT / original['path'], original['sha256'])
        clean = {'A': task_a.clean, 'B': task_b.clean}[task]
        normalized, reasons = clean(sid, source, profiles[sid])
        changed = source != normalized
        if changed != bool(reasons):
            raise ValueError(f'Missing or spurious cleanup reason: {sid}')
        # Parse for syntax only. Participant programs are never imported here.
        compile(normalized, '<cleaned-start>', 'exec')
        path = RUN / 'sources' / sid / 'src/solution.py'
        write_same(path, normalized)
        patch_record = None
        if changed:
            diff = difflib.unified_diff(source.decode().splitlines(keepends=True),
                                        normalized.decode().splitlines(keepends=True),
                                        fromfile=f'{sid}/original/solution.py',
                                        tofile=f'{sid}/cleaned/solution.py')
            patch = ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'
                            for line in diff).encode()
            patch_path = RUN / 'patches' / f'{sid}.diff'
            write_same(patch_path, patch)
            patch_record = artifact(patch_path, patch)
        conditions = {}
        for condition in ('RR', 'SA', 'EW'):
            rec = row['conditions'][condition]
            folder = RUN / 'packets' / sid / condition
            expected = {'workspace/src/solution.py', 'condition_context.md', 'prompt_draft.md'}
            if set(rec['files']) != expected:
                raise ValueError(f'Unexpected packet inventory: {sid}/{condition}')
            for name, file in rec['files'].items():
                old = read_checked(PACKETS / rec['path'] / name, file['sha256'])
                if name == 'workspace/src/solution.py' and old != source:
                    raise ValueError(f'Packet source differs from original: {sid}/{condition}')
                write_same(folder / name, normalized if name == 'workspace/src/solution.py' else old)
            conditions[condition] = {'packet_dir': str(folder), 'prompt_sha256': rec['files']['prompt_draft.md']['sha256']}
        records[sid] = {
            'participant_id': sid, 'task': task, 'group': group,
            'original_source': original, 'cleaned_source': artifact(path, normalized),
            'original_profile': profiles[sid], 'target_profile': 'iso_primary' if task == 'A' else 'boolean',
            'changed': changed, 'changes': reasons, 'patch': patch_record, 'conditions': conditions,
        }
    sessions = []
    for previous in selection['sessions']:
        row = records[previous['participant_id']]
        packet = row['conditions'][previous['condition']]
        if packet['prompt_sha256'] != previous['prompt_sha256']:
            raise ValueError('Frozen prompts differ')
        plan = deepcopy(previous)
        plan.update(packet, source_sha256=row['cleaned_source']['sha256'],
                    settings_status='CLEANED_STARTS_OFFLINE_CANDIDATE')
        sessions.append(plan)
    obj = {
        'status': 'OFFLINE_CLEANED_INPUTS', 'live_enabled': False,
        'parent_selection_sha256': SELECTION_HASH, 'programs': list(records.values()),
        'sessions': sessions,
    }
    write_same(RUN / 'preparation.json', encode(obj))
    print(f"Prepared {len(records)} source copies and {len(sessions)} session bindings. "
          f"{sum(r['changed'] for r in records.values())} source files normalized.", flush=True)
    return obj


if __name__ == '__main__':
    build()
