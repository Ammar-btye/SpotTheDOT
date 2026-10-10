"""Score the template baseline and a served model on the same approved saved packets (offline harness, EVAL-09).

From amd/system2 (no GPU or network needed for the template runner):

    uv run --no-project --with-requirements requirements.txt python scripts/evaluate.py --runner template
    python scripts/evaluate.py --runner both --model-url http://127.0.0.1:8080 --model qwen3.5-9b-q4km \
        --label amd-gfx1151-rocm --out-dir results/eval/qwen35-9b
    python scripts/evaluate.py --runner template --limit 2 --seed 7 --out-dir /tmp/eval-smoke

Writes <out-dir>/cases.jsonl (one record per runner x case), report.md and metrics.json (written last; its presence
means the run completed). Exit 0 = run completed, including model failures, which are counted and fall back to the
checked template; 1 = dataset rejected (unreadable, empty, missing manifest, changed, leaking, holdout or future
evidence, malformed reference), before any model call or output write; 2 = usage error; 3 = the run failed after the
dataset was accepted (runner setup such as few-shot loading, or an error mid-run such as a packet-identity mismatch
or an unavailable entity catalog): the error class is printed, no capture content, and no output is written. The
dataset defaults to the approved training packets in data/dev_packets.json; results there are development numbers,
never headline numbers.
"""
import argparse
import os
from pathlib import Path
import sys
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyst.evaluation import (DEFAULT_DATASET, DEFAULT_SEED, EvalConfig, ModelRunner, TemplateRunner,  # noqa: E402
                                load_eval_dataset, report, run_evaluation, write_artifacts)
from analyst.generation import MAX_TOKENS, LlamaGenerator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET, help='approved saved-packet dataset')
    parser.add_argument('--runner', choices=('template', 'model', 'both'), default='template')
    parser.add_argument('--model-url', help='llama-server base URL, e.g. http://127.0.0.1:8080 (model/both)')
    parser.add_argument('--model', help='model ID sent to the server and recorded in the identity')
    parser.add_argument('--out-dir', type=Path, help='default results/eval/<runner>')
    parser.add_argument('--label', default='unlabelled', help='where the measurement ran, e.g. amd-gfx1151-rocm')
    parser.add_argument('--limit', type=int, help='smoke knob: seeded sample of N cases')
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    parser.add_argument('--deadline-s', type=float, default=15.0, help='per-case pipeline budget, seconds')
    parser.add_argument('--timeout-s', type=float, default=15.0, help='per HTTP call, seconds')
    parser.add_argument('--max-tokens', type=int, default=MAX_TOKENS)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args(argv)
    wants_model = args.runner in ('model', 'both')
    if wants_model and not args.model_url:
        parser.error('--model-url is required for --runner model|both')
    if wants_model and (urllib.parse.urlsplit(args.model_url).scheme not in ('http', 'https')
                        or not urllib.parse.urlsplit(args.model_url).hostname):
        parser.error('--model-url must be http(s)://host[:port]')
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be at least 1')
    if args.deadline_s <= 0 or args.timeout_s <= 0 or args.max_tokens <= 0:
        parser.error('--deadline-s, --timeout-s and --max-tokens must be positive')
    out_dir = args.out_dir or ROOT / 'results' / 'eval' / args.runner
    config = EvalConfig(seed=args.seed, limit=args.limit, deadline_s=args.deadline_s, timeout_s=args.timeout_s,
                        max_tokens=args.max_tokens, model_url=args.model_url if wants_model else None,
                        model=args.model if wants_model else None, label=args.label)
    try:
        dataset = load_eval_dataset(args.dataset)
    except ValueError:
        # Deliberately generic: rejected captures must not be echoed into logs.
        print('Evaluation dataset rejected: invalid provenance, leakage, manifest, reference or packet identity.',
              file=sys.stderr)
        return 1
    stage = 'runner setup'
    try:
        runners = [TemplateRunner()] if args.runner in ('template', 'both') else []
        if wants_model:
            runners.append(ModelRunner(LlamaGenerator(args.model_url, model=args.model, max_tokens=args.max_tokens,
                                                      timeout_s=args.timeout_s,
                                                      api_key=os.environ.get('SYSTEM2_LLAMA_API_KEY') or None)))
        stage = 'evaluation run'
        metrics = run_evaluation(dataset, runners, config)
    except ValueError as exc:
        # Class name only (a pydantic message can quote packet content); nothing is written for a failed run.
        print('Evaluation failed during %s (dataset was accepted): %s. No results written.'
              % (stage, type(exc).__name__), file=sys.stderr)
        return 3
    write_artifacts(out_dir, metrics)
    if not args.quiet:
        print(report({k: v for k, v in metrics.items() if k != 'records'}))
    for name, agg in metrics['runners'].items():
        acc = agg['generation']['model_accepted']
        print('%s | %d cases | public valid %d/%d | model accepted %s | p95 %s ms | %s' % (
            name, agg['cases'], agg['public_response_valid']['count'], agg['cases'],
            'n/a' if acc['value'] is None else '%d/%d' % (acc['count'], acc['denominator']),
            agg['latency_ms']['p95'], out_dir / 'metrics.json'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
