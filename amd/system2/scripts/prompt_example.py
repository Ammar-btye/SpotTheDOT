"""Render the exact chat request System 2 sends for a multimodal fixture (PROMPT_FORMAT.md). Run from amd/system2:

    python scripts/prompt_example.py                                   # print the gauge_disagree request
    python scripts/prompt_example.py --write                           # refresh the committed .messages.json
    python scripts/prompt_example.py --text-only                       # the text-only resend (no image part)

The output is the OpenAI /v1/chat/completions body minus nothing: model, messages (system, three few-shot pairs,
then the current user content array), temperature, max_tokens, response_format json_schema and
chat_template_kwargs, plus the fixture's training-target reply as the assistant turn a fine-tune should learn.
tests/test_multimodal.py fails when the committed file drifts from what the code builds.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyst.backend_contract import BackendAssessRequest  # noqa: E402
from analyst.generation import request_body  # noqa: E402
from analyst.packet import normalize_packet  # noqa: E402
from analyst.prompts import FEWSHOT_COUNT, PROMPT_VERSION, load_examples, select_examples  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures' / 'multimodal' / 'gauge_disagree.json'
VISION_MODEL = 'system2-vision'   # the gateway alias (amd/gateway/config.yaml); SYSTEM2_VISION_MODEL in compose
TEXT_MODEL = 'system2'


def render(fixture: Path = FIXTURE, text_only: bool = False) -> dict:
    d = json.loads(Path(fixture).read_text(encoding='utf-8'))
    prepared = normalize_packet(BackendAssessRequest.model_validate(d['request']))
    chosen = select_examples(load_examples(), prepared, FEWSHOT_COUNT)
    body = request_body(prepared, chosen, (), TEXT_MODEL if text_only else VISION_MODEL,
                        include_image=not text_only)
    return {'prompt_version': PROMPT_VERSION, 'fixture': Path(fixture).name, 'request_body': body,
            'target_reply': d['reply']}


def output_path(fixture: Path = FIXTURE) -> Path:
    return Path(fixture).with_suffix('.messages.json')


def dumps(rendered: dict) -> str:
    return json.dumps(rendered, indent=1, ensure_ascii=False) + '\n'


def main():
    ap = argparse.ArgumentParser(description='Render the exact multimodal chat request for a fixture.')
    ap.add_argument('--fixture', default=str(FIXTURE))
    ap.add_argument('--text-only', action='store_true', help='the text-only resend (image rejected)')
    ap.add_argument('--write', action='store_true', help='write <fixture>.messages.json next to the fixture')
    args = ap.parse_args()
    text = dumps(render(Path(args.fixture), args.text_only))
    if args.write:
        if args.text_only:
            ap.error('--write stores the image request only')
        output_path(Path(args.fixture)).write_text(text, encoding='utf-8')
        print('wrote %s' % output_path(Path(args.fixture)))
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
