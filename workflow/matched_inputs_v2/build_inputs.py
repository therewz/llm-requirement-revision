"""Build concise matched drafts; no participant execution or provider calls."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'runs/matched_inputs_v1'
OLD_MANIFEST_SHA = 'c8fa64e6be610d703928a11a447433c85524c3d583ab79e72435b2a30869c254'
spec = importlib.util.spec_from_file_location('preserved_input_helpers', ROOT / 'code/matched_inputs_v1/build_inputs.py')
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)

INTRO = ('Revise the existing Python implementation to satisfy the current requirements below. '
         'Treat these requirements as authoritative. Remove restrictions they do not require, '
         'preserve all specified functionality, and avoid unrelated changes. '
         'If no changes are needed, leave the implementation unchanged.')
ENDING = 'Briefly summarize any changes.'
RR_NOTICE = ('The following additional requirement is active and takes precedence '
             'where it conflicts with the requirements above:')
EW_NOTICE = ('The following requirement has been withdrawn. Remove the restriction it introduced; '
             'it is not part of the current requirements:')


def condition_block(condition, requirement):
    if condition == 'SA':
        return ''
    title, notice = ('Additional requirement', RR_NOTICE) if condition == 'RR' else ('Requirement withdrawal', EW_NOTICE)
    if condition not in ('RR', 'EW'):
        raise ValueError(condition)
    return f'**{title}**\n\n{notice}\n\n{requirement}\n\n'


def build(output):
    output = Path(output)
    old_bytes = (OLD / 'build_manifest.json').read_bytes()
    assert v1.digest(old_bytes) == OLD_MANIFEST_SHA, 'Preserved v1 manifest changed'
    old = json.loads(old_bytes)
    helper_bytes = (ROOT / old['build_code']['path']).read_bytes()
    assert v1.digest(helper_bytes) == old['build_code']['sha256'], 'Preserved v1 helper changed'
    tasks = v1.load_task_texts()
    assert tasks == old['tasks']
    records = []
    for row in old['records']:
        sid, task = row['participant_id'], row['task']
        source = v1.checked_bytes(row['source_code']['path'], row['source_code']['sha256'])
        specs = row['phase_i_specification']
        raw = v1.checked_bytes(specs[0]['path'], specs[0]['sha256']) if specs else None
        current = '### Task description\n\n' + tasks[task]['description']
        if raw is not None:
            current += '\n\n### Specification\n\n' + v1.fenced_json(raw)
        prompts, conditions = {}, {}
        for condition in ('RR', 'SA', 'EW'):
            previous = row['conditions'][condition]
            for name, rec in previous['files'].items():
                assert v1.digest((OLD / previous['path'] / name).read_bytes()) == rec['sha256']
            block = condition_block(condition, tasks[task]['requirement'])
            context = '**Current requirements**\n\n' + current + '\n\n' + block
            prompt = INTRO + '\n\n' + context + ENDING + '\n'
            folder = output / 'packets' / sid / condition
            files = {'workspace/src/solution.py': source, 'condition_context.md': context.encode(),
                     'prompt_draft.md': prompt.encode()}
            for name, data in files.items():
                v1.write_same(folder / name, data)
            assert {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()} == set(files)
            conditions[condition] = {'path': f'packets/{sid}/{condition}', 'files': {
                name: {'sha256': v1.digest(data), 'bytes': len(data)} for name, data in files.items()}}
            prompts[condition] = prompt
        for condition in ('RR', 'EW'):
            block = condition_block(condition, tasks[task]['requirement'])
            assert prompts[condition].replace(block, '', 1) == prompts['SA']
        records.append({**row, 'conditions': conditions})
    manifest = {**old, 'schema_version': 2,
                'status': 'SIMPLIFIED_MATCHED_DRAFTS_PENDING_EXECUTION_MODE_AND_SCORING_POLICY',
                'build_code': v1.source_record(Path(__file__), Path(__file__).read_bytes()),
                'helper_code': old['build_code'],
                'parent_manifest': v1.source_record(OLD / 'build_manifest.json', old_bytes),
                'shared_instruction': INTRO, 'shared_ending': ENDING,
                'condition_notices': {'RR': RR_NOTICE, 'SA': None, 'EW': EW_NOTICE},
                'wording_changes': [
                    'User-authorized simplification; this is adapted wording, not verbatim Maleknaz.',
                    'Repeated role/inspection/preservation boilerplate removed; authority and no unrelated changes retained.',
                    'RR active-update priority is now explicit; this resolves the previously recorded hierarchy issue.',
                    'EW notice shortened while the full original three behavioral sentences stay exact.',
                    'Neutral Task description/Specification headings replace researcher phase labels.',
                    'Original task paragraphs, own raw JSON specifications and original P2 source bytes unchanged.',
                    'Original lab process sentence remains omitted as in v1; no further requirement truncation.',
                    'Execution/output policy remains pending; no tools, tests or model settings enabled.'
                ],
                'prompt_source': {'derivation': 'User-authorized concise adaptation of Maleknaz prompts',
                                  'original_correspondence': old['prompt_source'],
                                  'current_wording_defined_in': 'build_code'},
                'specification_audit': {'path': 'reports/matched_inputs_v1/specification_audit/summary.json',
                                        'sha256': v1.digest((ROOT / 'reports/matched_inputs_v1/specification_audit/summary.json').read_bytes()),
                                        'issues_unchanged': True},
                'records': records}
    v1.write_same(output / 'build_manifest.json', (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode())
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'runs/matched_inputs_v2')
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({'participants': result['participant_count'], 'packets': result['packet_count'], 'live_enabled': False}))
