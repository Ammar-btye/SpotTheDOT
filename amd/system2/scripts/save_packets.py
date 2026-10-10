"""Offline captures → approved packets. No MCP/Neon calls or holdout overrides.

From the repository root:

    python amd/system2/scripts/save_packets.py --seed --output amd/system2/data/dev_packets.json
    python amd/system2/scripts/save_packets.py --heldout --output amd/system2/data/heldout_packets.json
    python amd/system2/scripts/save_packets.py --input capture.json --output /tmp/approved.json

--seed and --input publish training-mission packets (split 'train'); --heldout publishes the controlled System 1
fold-2 held-out set (split 'heldout') that Phase 4 headline numbers are computed on. Imports are train-only.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyst.dataset import dataset_manifest, heldout_dataset, seed_dataset, validate_dataset


def approve_import(value):
    """Drop transport diagnostics only after remaining evidence passes approval.

    This is a narrow allow-list of known non-evidence diagnostics, never a generic
    recursive label scrubber. Ambiguous evidence fields still fail validation.
    """
    candidate = copy.deepcopy(value)
    if not isinstance(candidate, dict) or not isinstance(candidate.get('cases'), list):
        return validate_dataset(candidate)
    changed = False
    for case in candidate['cases']:
        if not isinstance(case, dict) or not isinstance(case.get('request'), dict):
            continue
        request = case['request']
        context = request.get('context')
        if isinstance(context, dict):
            # Forbidden diagnostics are rejected by key name whatever their value, so drop them even when empty.
            for key in ('explanations', 'prior_answers', 'previous_output'):
                if key in context:
                    context.pop(key)
                    changed = True
            # system1 is a real evidence section: an empty one already approved must not change the hash.
            if context.get('system1'):
                context.pop('system1')
                changed = True
        flag = request.get('flag')
        if isinstance(flag, dict):
            for key in ('labels', 'explanation', 'previous_output'):
                if key in flag:
                    flag.pop(key)
                    changed = True
    # Sanitization changes the artifact, so a previously supplied hash cannot
    # certify it. Strict validation below proves the actual safe evidence first.
    if changed:
        candidate.pop('manifest', None)
    return validate_dataset(candidate)


def publish(value, output: Path, split: str = 'train'):
    # Validation and serialization precede *any* output filesystem mutation.
    cases = validate_dataset(value, split)
    approved = {'cases': [c.to_dict() for c in cases], 'manifest': dataset_manifest(cases)}
    payload = (json.dumps(approved, ensure_ascii=False, sort_keys=True, indent=2,
                          allow_nan=False) + '\n').encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.' + output.name + '-',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)    # NamedTemporaryFile creates 0600; the image's non-root user must read it
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return approved['manifest']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument('--input', type=Path)
    sources.add_argument('--seed', action='store_true', help='reproduce checked-in development packets')
    sources.add_argument('--heldout', action='store_true', help='reproduce the checked-in fold-2 held-out packets')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.seed:
            value = seed_dataset()
        elif args.heldout:
            value = heldout_dataset()
        else:
            value = json.loads(args.input.read_text(encoding='utf-8'))
            cases = approve_import(value)
            value = {'cases': [c.to_dict() for c in cases], 'manifest': dataset_manifest(cases)}
        manifest = publish(value, args.output, 'heldout' if args.heldout else 'train')
    except (ValueError, OSError, KeyError, TypeError):
        # Error payloads deliberately exclude capture content and diagnostics.
        print('Saved capture rejected: invalid source lineage, provenance, split, or packet structure.', file=sys.stderr)
        return 1
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
