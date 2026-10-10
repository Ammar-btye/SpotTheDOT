"""Fill the System 2 explanation cache for a list of /v1/assess requests (SRV-02), so the dashboard reads precomputed.

From amd/system2, with llama-server up (docs/RUNNING.md):

    SYSTEM2_LLAMA_URL=http://127.0.0.1:8080 SYSTEM2_MODEL=qwen3.5-9b-q4km \
        python scripts/precompute.py --requests data/dev_packets.json fixtures/backend/*.json
    python scripts/precompute.py --requests flags.jsonl --model-url http://127.0.0.1:8080 --model qwen3.5-9b-q4km \
        --cache-dir /tmp/s2-cache --limit 3
    python scripts/precompute.py --requests flags.jsonl --refresh      # regenerate even when cached

Requests come from approved-dataset files ({"cases": [{"request": ...}]}), fixture files ({"request": ...}), JSON
lists or .jsonl lines. Every request goes through the same LiveAssessor.assess as the live API, so it writes the same
<cache-dir>/<sha256>.json entries the API reads (key: flag_id, packet_hash, model, prompt_ver); only checked llm/retry
results are stored, and a second run over unchanged requests generates nothing. Prints one line per request and a
"|"-separated summary with p50/p95 latency over this run's generations.
Exit 0 = done (fallbacks included); 1 = a request was rejected before any model call; 2 = usage or config error
(no URL/model, no cache dir, few-shots or entity catalog unavailable).
"""
import argparse
import json
import os
from pathlib import Path
import sys
from typing import List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyst.backend_contract import BackendAssessRequest  # noqa: E402
from analyst.evaluation import endpoint, latency_summary  # noqa: E402
from analyst.grounding import default_catalog  # noqa: E402
from analyst.live import (CACHE_ENV, DEADLINE_S, MODEL_ENV, URL_ENV, ExplanationCache, LiveAssessor,  # noqa: E402
                          cache_dir_from_env)
from analyst.packet import normalize_packet  # noqa: E402
from analyst.pipeline import PipelineConfig  # noqa: E402

GENERATED_PATHS = ('llm', 'retry', 'fallback')   # the pipeline called the generator


def _unwrap(obj, source: str) -> List[Tuple[str, object]]:
    if isinstance(obj, dict) and isinstance(obj.get('cases'), list):
        return [('%s[%d]' % (source, i), c.get('request') if isinstance(c, dict) else c)
                for i, c in enumerate(obj['cases'])]
    if isinstance(obj, dict) and 'request' in obj:
        return [('%s[0]' % source, obj['request'])]
    if isinstance(obj, list):
        return [('%s[%d]' % (source, i), o['request'] if isinstance(o, dict) and 'request' in o else o)
                for i, o in enumerate(obj)]
    return [('%s[0]' % source, obj)]


def load_requests(paths: Sequence) -> List[Tuple[str, BackendAssessRequest]]:
    """[(source[index], request)], every one validated and normalized; ValueError naming the source and index."""
    raw = []
    for path in paths:
        path = Path(path)
        try:
            text = path.read_text(encoding='utf-8')
        except OSError as exc:
            raise ValueError('%s: unreadable (%s)' % (path, type(exc).__name__)) from None
        try:
            if path.suffix == '.jsonl':
                for n, line in enumerate(text.splitlines()):
                    if line.strip():
                        raw.extend(_unwrap(json.loads(line), '%s:%d' % (path, n + 1)))
            else:
                raw.extend(_unwrap(json.loads(text), str(path)))
        except ValueError as exc:
            raise ValueError('%s: not JSON (%s)' % (path, str(exc).splitlines()[0])) from None
    out = []
    for source, obj in raw:
        try:
            body = BackendAssessRequest.model_validate(obj)
            normalize_packet(body)
        except ValueError as exc:    # pydantic ValidationError is a ValueError
            raise ValueError('%s: invalid request: %s' % (source, str(exc).splitlines()[0])) from None
        out.append((source, body))
    if not out:
        raise ValueError('no requests in %s' % ', '.join(str(p) for p in paths))
    return out


def run_precompute(items: Sequence[Tuple[str, BackendAssessRequest]], assessor: LiveAssessor,
                   refresh: bool = False) -> dict:
    """Assess every request through the cache; counts plus latency_summary over this run's generations."""
    counts = dict(requests=0, cached=0, generated=0, fallback=0, insufficient_context=0, not_stored=0)
    latencies = []
    for source, body in items:
        resp, status, stored = assessor.assess_detail(body, refresh=refresh)
        counts['requests'] += 1
        if status == 'hit':
            counts['cached'] += 1
        else:
            if resp.path in GENERATED_PATHS:
                counts['generated'] += 1
                latencies.append(resp.latency_ms)
            if resp.path in ('fallback', 'insufficient_context'):
                counts[resp.path] += 1
            if not stored:
                counts['not_stored'] += 1
        print('flag %d | %s | path %s | %d ms' % (resp.flag_id, status, resp.path, resp.latency_ms), flush=True)
    counts['latency'] = latency_summary(latencies)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--requests', nargs='+', required=True, help='dataset, fixture, JSON list or .jsonl files')
    parser.add_argument('--model-url', default=None, help='llama-server base URL (default env %s)' % URL_ENV)
    parser.add_argument('--model', default=None, help='served model name, part of the cache key (default env %s)'
                        % MODEL_ENV)
    parser.add_argument('--cache-dir', type=Path, default=None,
                        help='explanation cache (default env %s, else amd/system2/cache)' % CACHE_ENV)
    parser.add_argument('--refresh', action='store_true', help='regenerate even when a cached entry is valid')
    parser.add_argument('--limit', type=int, help='smoke knob: only the first N requests')
    parser.add_argument('--deadline-s', type=float, default=DEADLINE_S, help='per-request pipeline budget, seconds')
    args = parser.parse_args(argv)
    url = (args.model_url or os.environ.get(URL_ENV) or '').strip()
    model = (args.model or os.environ.get(MODEL_ENV) or '').strip()
    cache_dir = args.cache_dir or cache_dir_from_env()
    if not url:
        parser.error('--model-url or %s is required' % URL_ENV)
    if not model:
        parser.error('--model or %s is required' % MODEL_ENV)
    if cache_dir is None:
        parser.error('--cache-dir or %s is required outside a checkout' % CACHE_ENV)
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be at least 1')
    if args.deadline_s <= 0:
        parser.error('--deadline-s must be positive')
    try:
        items = load_requests(args.requests)
    except ValueError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        sys.exit(1)
    items = items[:args.limit] if args.limit else items
    from analyst.generation import LlamaGenerator
    try:
        generator = LlamaGenerator(url, model=model)
        assessor = LiveAssessor(generator, model, PipelineConfig(deadline_s=args.deadline_s, catalog=default_catalog()),
                                cache=ExplanationCache(cache_dir))
    except (ValueError, OSError) as exc:
        print('ERROR: live config unusable (%s): %s' % (endpoint(url), str(exc).splitlines()[0] if str(exc) else
                                                         type(exc).__name__), file=sys.stderr)
        sys.exit(2)
    print('precompute | model %s via %s | %d requests | cache %s' % (model, endpoint(url), len(items), cache_dir),
          flush=True)
    c = run_precompute(items, assessor, refresh=args.refresh)
    lat = c['latency']
    print('requests %d | cached %d | generated %d | fallback %d | insufficient_context %d | not_stored %d | '
          'p50 %s ms | p95 %s ms | max %s ms'
          % (c['requests'], c['cached'], c['generated'], c['fallback'], c['insufficient_context'], c['not_stored'],
             lat['p50'], lat['p95'], lat['max']), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
