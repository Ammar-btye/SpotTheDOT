"""One command for the defendable System 2 report: held-out headline with mission-level CIs (EVAL-01).

From amd/system2 (the template runner needs no GPU or network):

    uv run --no-project --with-requirements requirements.txt python scripts/report.py --runner template
    python scripts/report.py --runner both --model-url http://127.0.0.1:8080 --model qwen3.5-9b-q4km \
        --label amd-gfx1151-rocm-qwen35-9b-q4km --out-dir results/report/qwen35-9b
    python scripts/report.py --rebuild results/report/qwen35-9b

Runs the same runner objects over the approved held-out packets (data/heldout_packets.json, the headline) and the
training-pool dev packets (data/dev_packets.json, a separate section that is never headline). Writes
<out-dir>/cases.jsonl (one record per section x runner x flag), report.md and metrics.json (written last; its presence
means the run completed). Exit 0 = report written; 1 = a dataset was rejected (unreadable, tampered, or not the
expected split) before any model call or output write; 2 = usage error; 3 = the run failed after the datasets were
accepted (class name printed, no capture content, nothing written).
"""
import argparse
import dataclasses
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shlex
import sys
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyst.dataset import content_hash  # noqa: E402
from analyst.evaluation import (DEFAULT_SEED, EvalConfig, ModelRunner, TemplateRunner, endpoint,  # noqa: E402
                                is_loopback, load_eval_dataset, publish_files, run_evaluation)
from analyst.generation import MAX_TOKENS, LlamaGenerator  # noqa: E402
from analyst.headline import CI_RESAMPLES, CI_SEED, build_metrics, heldout_scope, render  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / 'data' / 'heldout_packets.json'
DEV = ROOT / 'data' / 'dev_packets.json'
REJECTED = 'Report dataset rejected: invalid provenance, leakage, manifest, split or packet identity.'


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def command_line(argv) -> str:
    """The invocation as recorded in the report, with any --model-url reduced to a credential-free endpoint."""
    out, it = [], iter(argv)
    for a in it:
        if a == '--model-url':
            out += [a, endpoint(next(it, '')) or '']
        elif a.startswith('--model-url='):
            out.append('--model-url=' + (endpoint(a.split('=', 1)[1]) or ''))
        else:
            out.append(a)
    return ' '.join(['python', 'scripts/report.py'] + [shlex.quote(a) for a in out])


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--runner', choices=('template', 'both'), default='template')
    p.add_argument('--heldout', type=Path, default=HELDOUT, help='approved held-out packets (split heldout)')
    p.add_argument('--dev', type=Path, default=DEV, help='approved training-pool packets (split train)')
    p.add_argument('--no-dev', action='store_true', help='skip the development section')
    p.add_argument('--model-url', help='llama-server base URL, e.g. http://127.0.0.1:8080 (--runner both)')
    p.add_argument('--model', help='model ID sent to the server and recorded in the identity')
    p.add_argument('--label', help='where the measurement ran, e.g. amd-gfx1151-rocm-qwen35-9b-q4km')
    p.add_argument('--limit', type=int, help='smoke knob: seeded sample of N held-out flags (never headline)')
    p.add_argument('--seed', type=int, default=DEFAULT_SEED)
    p.add_argument('--deadline-s', type=float, default=15.0, help='per-flag pipeline budget, seconds')
    p.add_argument('--timeout-s', type=float, default=15.0, help='per HTTP call, seconds')
    p.add_argument('--max-tokens', type=int, default=MAX_TOKENS)
    p.add_argument('--ci-resamples', type=int, default=CI_RESAMPLES)
    p.add_argument('--ci-seed', type=int, default=CI_SEED)
    p.add_argument('--out-dir', type=Path, help='default results/report/<runner>')
    p.add_argument('--quiet', action='store_true')
    return p


def _load(path: Path, split: str):
    dataset = load_eval_dataset(path)
    if dataset.split != split:
        raise ValueError('expected split %s' % split)
    return dataset


def run(args, argv) -> int:
    wants_model = args.runner == 'both'
    out_dir = args.out_dir or ROOT / 'results' / 'report' / args.runner
    try:
        heldout = _load(args.heldout, 'heldout')
        dev = None if args.no_dev else _load(args.dev, 'train')
    except ValueError:
        print(REJECTED, file=sys.stderr)       # deliberately generic: rejected captures are never echoed
        return 1
    config = EvalConfig(seed=args.seed, limit=args.limit, deadline_s=args.deadline_s, timeout_s=args.timeout_s,
                        max_tokens=args.max_tokens, model_url=args.model_url if wants_model else None,
                        model=args.model if wants_model else None, label=args.label)
    stage = 'runner setup'
    try:
        runners = [TemplateRunner()]
        if wants_model:
            runners.append(ModelRunner(LlamaGenerator(args.model_url, model=args.model, max_tokens=args.max_tokens,
                                                      timeout_s=args.timeout_s)))
        stage = 'evaluation run'
        started = utc_now()
        h = run_evaluation(heldout, runners, config)
        d = None if dev is None else run_evaluation(dev, runners, dataclasses.replace(config, limit=None))
        finished = utc_now()
        memory = None
    except ValueError as exc:
        print('Report failed during %s (datasets were accepted): %s. No results written.'
              % (stage, type(exc).__name__), file=sys.stderr)
        return 3
    records = [dict(r, section='heldout') for r in h['records']]
    records += [] if d is None else [dict(r, section='development') for r in d['records']]
    identity = {'heldout': h['identity'], 'development': None if d is None else d['identity']}
    identity['identity_hash'] = content_hash(identity)
    url = config.model_url
    context = {
        'ci': {'resamples': args.ci_resamples, 'seed': args.ci_seed},
        'identity': identity,
        'heldout_scope': heldout_scope(h['scope']['headline_eligible']),
        'measurement': {'label': args.label, 'endpoint': endpoint(url), 'endpoint_loopback': is_loopback(url),
                        'host': platform.node(), 'source': 'http model endpoint + in-process template' if url
                        else 'in-process template', 'started_at': started, 'finished_at': finished},
        'command': {'run': command_line(argv), 'rebuild': 'python scripts/report.py --rebuild %s' % out_dir},
        'memory': memory,
    }
    metrics = build_metrics(records, context)
    text = render(metrics)
    publish_files(out_dir, [
        ('cases.jsonl', ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n'
                                for r in records).encode('utf-8')),
        ('report.md', text.encode('utf-8')),
        ('metrics.json', dump(metrics)),
    ])
    if not args.quiet:
        print(text)
    print('report | %d held-out flags in %d missions | headline %s | %s' % (
        metrics['scope']['n_flags'], metrics['scope']['n_missions'],
        'eligible' if metrics['scope']['headline_eligible'] else 'NOT eligible', out_dir / 'metrics.json'))
    return 0


def dump(metrics: dict) -> bytes:
    return (json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    p = parser()
    args = p.parse_args(argv)
    if args.runner == 'both':
        if not args.model_url:
            p.error('--model-url is required for --runner both')
        parts = urllib.parse.urlsplit(args.model_url)
        if parts.scheme not in ('http', 'https') or not parts.hostname:
            p.error('--model-url must be http(s)://host[:port]')
    if args.label is None:
        args.label = 'unlabelled'
    if args.limit is not None and args.limit < 1:
        p.error('--limit must be at least 1')
    if args.deadline_s <= 0 or args.timeout_s <= 0 or args.max_tokens <= 0 or args.ci_resamples < 1:
        p.error('--deadline-s, --timeout-s, --max-tokens and --ci-resamples must be positive')
    return run(args, argv)


if __name__ == '__main__':
    raise SystemExit(main())
