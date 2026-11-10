"""Read original inputs from a previously accepted archive into a new run directory.

Does not repair or overwrite the original checkout. Individual source files must
match the preserved original-source hashes, in addition to the archive hash.
"""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'repositories/followup-offline-local-v2'
RUN=ROOT/'runs/withdrawal_keys_v1'
ARCHIVE=BASE/'dist/pilot_taska_v4_private_package.tar.gz'
EXPECTED='18032f548fd2bf7ac9407e8fc7f68e467f02f422e7011dd45978a557bf48fbef'


def main():
    data=ARCHIVE.read_bytes()
    assert hashlib.sha256(data).hexdigest()==EXPECTED
    manifest=BASE/'LOCAL_V3_MANIFEST_SHA256.json'
    expected={k:v for k,v in json.loads(manifest.read_text())['files'].items() if k.startswith('Data/')}
    actual={}
    destination=RUN/'input_snapshot'
    if destination.exists(): raise RuntimeError('Refuse overwrite')
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
        for member in archive.getmembers():
            parts=PurePosixPath(member.name).parts
            if len(parts)<2 or parts[1]!='Data' or not member.isfile(): continue
            rel=PurePosixPath(*parts[1:])
            assert '..' not in rel.parts and not rel.is_absolute()
            assert str(rel) not in actual
            payload=archive.extractfile(member).read()
            digest=hashlib.sha256(payload).hexdigest()
            assert expected[str(rel)]==digest,(str(rel),digest)
            out=destination/str(rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(payload)
            actual[str(rel)]=digest
    assert actual==expected
    (RUN/'input_recovery.json').write_text(json.dumps({
        'reason':'Local working-tree file reads stalled and git reported a truncated packfile; use verified archive without modifying originals.',
        'original_source_commit':'d6beb6ba31e5fc38e140df154ad3de5eec3bd88f',
        'archive_path':str(ARCHIVE.relative_to(ROOT)),'archive_sha256':EXPECTED,
        'comparison_manifest':str(manifest.relative_to(ROOT)),
        'comparison_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'verified_original_files':len(actual),'data_hashes':actual,
        'original_checkout_modified':False},indent=2)+'\n')
    print('Recovered and verified',len(actual),'original files into new run snapshot')


if __name__=='__main__':main()
