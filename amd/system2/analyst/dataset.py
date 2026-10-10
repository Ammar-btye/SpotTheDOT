"""Fail-closed offline saved-case approval against checked-in kit sources."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .backend_contract import BackendAssessRequest
from .packet import normalize_packet

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / 'amd/system1/data/kit'
POLICY_VERSION = 'saved-kit-fold2-asof-v1'
HOLDOUT_MISSIONS = frozenset({'M006', 'M009', 'M012', 'M013', 'M017', 'M018', 'M019', 'M020', 'M023'})
CATEGORIES = frozenset({'equipment', 'robot_health', 'navigation', 'data_quality', 'mission', 'insufficient_context'})
KEYS = {'actions': 'action_id', 'readings': 'reading_id', 'anomalies': 'anomaly_id',
        'missions': 'mission_id', 'assets': 'asset_id', 'locations': 'location_id'}
SECTIONS = ('facts', 'manual', 'policy', 'similar_incidents', 'asset_history', 'system1')
FORBIDDEN = frozenset({'labels', 'label', 'target', 'targets', 'expected', 'expected_action',
    'reference', 'scoring_reference', 'answer', 'explanation', 'explanations', 'previous_output',
    'prior_answer', 'prior_answers', 'generated_answer', 'assessment', 'assessments', 'true_health',
    'success_rate_pct', 'n_success', 'actions_total', 'actions_failed', 'anomalies_by_severity',
    'failure_types', 'ci95_pct', 'worst_anomaly'})


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def content_hash(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def source_tables() -> dict:
    tables = {}
    for table, key in KEYS.items():
        with (KIT / (table + '.csv')).open(encoding='utf-8', newline='') as stream:
            tables[table] = {r[key]: r for r in csv.DictReader(stream)}
    return tables


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('timestamp must be a string')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('invalid availability timestamp') from exc
    if parsed.tzinfo is not None or 'T' not in value:
        raise ValueError('timestamps must be naive site-local ISO datetimes')
    return parsed


def availability(table: str, row: dict) -> str | None:
    if table in ('assets', 'locations'):
        return None
    return row['end_time'] if table == 'missions' else row['timestamp']


def source_ref(table: str, row: dict) -> dict:
    return {'table': table, 'row_id': row[KEYS[table]], 'row_hash': content_hash(row),
            'available_at': availability(table, row)}


def row_fact(table: str, row: dict) -> str:
    """Exact source projection; never infer arithmetic or future facts."""
    fields = {
        'actions': ('action_id', 'mission_id', 'timestamp', 'action_type', 'location_id', 'asset_id',
                    'battery_pct', 'status', 'failure_type', 'duration_sec'),
        'readings': ('reading_id', 'action_id', 'mission_id', 'timestamp', 'asset_id', 'location_id',
                     'measurement_type', 'value', 'unit', 'quality'),
        'anomalies': ('anomaly_id', 'action_id', 'mission_id', 'timestamp', 'asset_id', 'location_id',
                      'anomaly_type', 'severity', 'description'),
        'missions': ('mission_id', 'mission_name', 'end_time', 'mission_status', 'start_battery_pct', 'end_battery_pct'),
        'assets': ('asset_id', 'asset_name', 'asset_type', 'location_id', 'criticality'),
        'locations': ('location_id', 'location_name', 'zone_type', 'environment'),
    }[table]
    return '; '.join('%s=%s' % (key, row[key]) for key in fields if row.get(key) != '')


def evidence_item(identifier: str, table: str, row: dict) -> dict:
    static = table in ('assets', 'locations')
    return {'id': identifier, 'fact': row_fact(table, row),
            'provenance': {'kind': 'static' if static else 'dynamic', 'source_rows': [source_ref(table, row)]}}


def _reject_leakage(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN or key.lower().startswith(('target_', 'expected_', 'prior_answer', 'previous_output')):
                raise ValueError('forbidden answer/label/aggregate field: %s' % key)
            _reject_leakage(child)
    elif isinstance(value, list):
        for child in value:
            _reject_leakage(child)


def _checked_rows(provenance, as_of, tables):
    if not isinstance(provenance, dict) or set(provenance) != {'kind', 'source_rows'}:
        raise ValueError('every evidence item requires known provenance')
    refs = provenance['source_rows']
    if not isinstance(refs, list) or not refs:
        raise ValueError('source_rows must be nonempty')
    checked = []
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {'table', 'row_id', 'row_hash', 'available_at'}:
            raise ValueError('unknown source-row provenance')
        table, row_id = ref['table'], ref['row_id']
        if not isinstance(table, str) or table not in tables or not isinstance(row_id, str) or row_id not in tables[table]:
            raise ValueError('source row not in checked-in kit')
        row = tables[table][row_id]
        if row.get('mission_id') in HOLDOUT_MISSIONS:
            raise ValueError('holdout source row prohibited')
        if ref != source_ref(table, row):
            raise ValueError('source hash or availability does not match source row')
        static = availability(table, row) is None
        if provenance['kind'] != ('static' if static else 'dynamic'):
            raise ValueError('provenance kind does not match source')
        if not static and _time(ref['available_at']) > as_of:
            raise ValueError('evidence not available at as_of')
        checked.append((table, row))
    return checked


def _check_item(item, as_of, tables):
    if not isinstance(item, dict):
        raise ValueError('evidence must be an object')
    provenance = item.get('provenance')
    if not isinstance(provenance, dict):
        raise ValueError('every evidence item requires provenance')
    if provenance.get('kind') == 'static_passage':
        if set(item) != {'id', 'text', 'provenance'}:
            raise ValueError('unsupported passage fields')
        if set(provenance) != {'kind', 'path', 'source_hash'} or provenance['path'] not in {
            'amd/system1/triage/policy.py', 'docs/backend-services-contract.md'}:
            raise ValueError('unknown static passage source')
        source = (ROOT / provenance['path']).read_bytes()
        if hashlib.sha256(source).hexdigest() != provenance['source_hash'] or not isinstance(item['text'], str) or not item['text'].strip() or item['text'] not in source.decode('utf-8'):
            raise ValueError('static passage does not match source')
    else:
        if set(item) != {'id', 'fact', 'provenance'}:
            raise ValueError('unsupported evidence fields or uncertified aggregate')
        rows = _checked_rows(provenance, as_of, tables)
        expected = ' | '.join(row_fact(table, row) for table, row in sorted(rows, key=lambda pair: (pair[0], pair[1][KEYS[pair[0]]])))
        if item['fact'] != expected:
            raise ValueError('evidence content is not the certified source projection')
    if not isinstance(item['id'], str) or not item['id'].strip():
        raise ValueError('citation id must be nonblank; spelling is never normalized')


def _canonical_item(item):
    """Canonical row order and identical duplicates without mutating captures."""
    if not isinstance(item, dict):
        raise ValueError('evidence must be an object')
    item = json.loads(canonical_bytes(item))
    provenance = item.get('provenance')
    if isinstance(provenance, dict) and isinstance(provenance.get('source_rows'), list):
        rows = provenance['source_rows']
        if any(not isinstance(row, dict) or not isinstance(row.get('table'), str)
               or not isinstance(row.get('row_id'), str) for row in rows):
            raise ValueError('invalid source row')
        unique = {}
        for row in rows:
            key = (row['table'], row['row_id'])
            if key in unique and unique[key] != row:
                raise ValueError('conflicting duplicate source row')
            unique[key] = row
        provenance['source_rows'] = [unique[key] for key in sorted(unique)]
    return item


@dataclass(frozen=True)
class SavedCase:
    case_id: str
    category: str
    mission_id: str
    as_of: str
    split: str
    _request_bytes: bytes
    _lineage_bytes: bytes
    _reference_bytes: bytes

    @property
    def request(self) -> BackendAssessRequest:
        return BackendAssessRequest.model_validate(json.loads(self._request_bytes))

    @property
    def prepared(self):
        return normalize_packet(self.request)

    @property
    def source_lineage(self):
        return json.loads(self._lineage_bytes)

    @property
    def reference(self):
        return json.loads(self._reference_bytes)

    def to_dict(self):
        result = {key: getattr(self, key) for key in ('case_id', 'category', 'mission_id', 'as_of', 'split')}
        return {**result, 'request': json.loads(self._request_bytes), 'source_lineage': self.source_lineage,
                'reference': self.reference}


def validate_dataset(value) -> tuple[SavedCase, ...]:
    if not isinstance(value, dict) or set(value) - {'cases', 'manifest'}:
        raise ValueError('dataset must contain cases and optional manifest')
    raw = value.get('cases')
    if not isinstance(raw, list) or not raw:
        raise ValueError('dataset must have at least one case')
    tables = source_tables()
    cases, identities = [], set()
    for record in raw:
        required = {'case_id', 'category', 'mission_id', 'as_of', 'split', 'request', 'source_lineage'}
        if not isinstance(record, dict) or required - set(record) or set(record) - required - {'reference'}:
            raise ValueError('invalid saved-case shape')
        if not isinstance(record['case_id'], str) or not record['case_id'].strip() or record['case_id'] in identities:
            raise ValueError('duplicate or invalid case_id')
        identities.add(record['case_id'])
        if record['category'] not in CATEGORIES or record['split'] != 'train':
            raise ValueError('only controlled training categories accepted')
        if record['mission_id'] not in tables['missions'] or record['mission_id'] in HOLDOUT_MISSIONS:
            raise ValueError('case must belong to a real training mission')
        as_of = _time(record['as_of'])
        mission = tables['missions'][record['mission_id']]
        if not _time(mission['start_time']) <= as_of <= _time(mission['end_time']):
            raise ValueError('as_of must be within mission event interval')
        request = record['request']
        _reject_leakage(request)
        if not isinstance(request, dict) or set(request) - {'flag_id', 'flag', 'context', 'request_id', 'event', 'reasons'}:
            raise ValueError('unsupported request fields')
        if request.get('event') or request.get('reasons') or request.get('flag') not in ({}, {'category': record['category']}):
            raise ValueError('unverified transport metadata')
        body = BackendAssessRequest.model_validate(request)
        context = body.context
        if set(context) - set(SECTIONS) - {'question', 'allowed_actions', 'suggested_action', 'missing', 'gaps', 'citation_ids', 'insufficient_context'}:
            raise ValueError('unverified context section')
        all_refs, seen = {}, {}
        approved = dict(context)
        for section in SECTIONS:
            items = context.get(section, [])
            if not isinstance(items, list):
                raise ValueError('evidence section must be a list')
            unique = {}
            for item in items:
                item = _canonical_item(item)
                _check_item(item, as_of, tables)
                item_bytes = canonical_bytes(item)
                if item['id'] in seen and seen[item['id']] != item_bytes:
                    raise ValueError('conflicting duplicate citation id')
                seen[item['id']] = item_bytes
                unique[item['id']] = item
                for ref in item['provenance'].get('source_rows', []):
                    all_refs[(ref['table'], ref['row_id'])] = ref
            if section in context:
                approved[section] = [unique[key] for key in sorted(unique)]
        lineage = sorted(all_refs.values(), key=lambda r: (r['table'], r['row_id']))
        given_lineage = record['source_lineage']
        if not isinstance(given_lineage, list) or sorted(given_lineage, key=lambda r: (r['table'], r['row_id'])) != lineage:
            raise ValueError('case lineage must match every evidence source row exactly')
        if lineage and not any(tables[r['table']][r['row_id']].get('mission_id') == record['mission_id'] for r in lineage):
            raise ValueError('case must contain evidence from its named mission')
        request = {**request, 'context': approved}
        prepared = normalize_packet(BackendAssessRequest.model_validate(request))
        if record['category'] == 'insufficient_context' and not prepared.insufficient_context:
            raise ValueError('insufficient-context case must be genuinely missing evidence')
        cases.append(SavedCase(record['case_id'], record['category'], record['mission_id'], record['as_of'],
                               record['split'], canonical_bytes(request), canonical_bytes(lineage),
                               canonical_bytes(record.get('reference'))))
    result = tuple(sorted(cases, key=lambda c: c.case_id))
    if 'manifest' in value and value['manifest'] != dataset_manifest(result):
        raise ValueError('dataset manifest mismatch')
    return result


def dataset_manifest(cases) -> dict:
    rows = [c.to_dict() for c in sorted(cases, key=lambda c: c.case_id)]
    payload = {'policy_version': POLICY_VERSION, 'holdout_fold': 2,
               'holdout_missions': sorted(HOLDOUT_MISSIONS), 'cases': rows}
    return {'policy_version': POLICY_VERSION, 'holdout_fold': 2,
            'holdout_missions': sorted(HOLDOUT_MISSIONS), 'case_count': len(rows),
            'content_hash': content_hash(payload)}


def load_dataset(path: str | Path) -> tuple[SavedCase, ...]:
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('cannot read saved dataset') from exc
    return validate_dataset(value)


def seed_dataset() -> dict:
    """Deterministic offline export, separate from backend's runtime retrieval."""
    import sys
    sys.path.insert(0, str(ROOT / 'amd/system1'))
    sys.path.insert(0, str(ROOT / 'amd/mcp'))
    from triage.kit import load_kit
    from triage.events import action_event
    from triage.policy import label_action
    from spot_mcp import domain

    kit = load_kit(KIT)
    tables = source_tables()
    if domain._POLICY_PATH.resolve() != (ROOT / 'amd/system1/triage/policy.py').resolve():
        raise ValueError('seed export requires the checked-in policy, not an environment override')
    vocabulary = domain.ALLOWED_ACTIONS
    selected = {}
    for action in kit.actions:
        if action['mission_id'] in HOLDOUT_MISSIONS:
            continue
        event = action_event(action, kit.missions[action['mission_id']], kit.locations[action['location_id']],
                             kit.assets[action['asset_id']], kit.readings.get(action['action_id']),
                             kit.anomalies.get(action['action_id']), 'kit')
        labelled = label_action(event)
        category = labelled['category']
        if category in ('equipment', 'robot_health', 'navigation', 'data_quality'):
            selected.setdefault(category, (action, labelled))
    records = []
    for index, category in enumerate(sorted(selected), 1):
        action, labelled = selected[category]
        row = tables['actions'][action['action_id']]
        facts = [evidence_item('F1', 'actions', row)]
        for table in ('readings', 'anomalies'):
            matches = [r for r in tables[table].values() if r['action_id'] == action['action_id']]
            for source in sorted(matches, key=lambda r: r[KEYS[table]]):
                facts.append(evidence_item('F%d' % (len(facts) + 1), table, source))
        as_of = max(r['available_at'] for f in facts for r in f['provenance']['source_rows'])
        action_facts = {**action, **(kit.anomalies.get(action['action_id']) or {}),
                        'environment': kit.locations[action['location_id']]['environment']}
        suggested = domain.suggested_action(category, labelled['priority'], action_facts)
        records.append(_seed_record(index, category, action['mission_id'], as_of, facts,
                                    vocabulary[category], suggested))
    mission = next(r for key, r in sorted(tables['missions'].items()) if key not in HOLDOUT_MISSIONS)
    records.append(_seed_record(5, 'mission', mission['mission_id'], mission['end_time'],
                               [evidence_item('F1', 'missions', mission)], vocabulary['mission'], 'REVIEW_MISSION'))
    records.append(_seed_record(6, 'insufficient_context', mission['mission_id'], mission['start_time'], [],
                               {'MANUAL_REVIEW': 'request operator review'}, 'MANUAL_REVIEW'))
    cases = validate_dataset({'cases': records})
    return {'cases': [c.to_dict() for c in cases], 'manifest': dataset_manifest(cases)}


def _seed_record(flag_id, category, mission_id, as_of, facts, actions, suggested):
    lineage = [r for f in facts for r in f['provenance']['source_rows']]
    return {'case_id': 'kit-' + category, 'category': category, 'mission_id': mission_id,
            'as_of': as_of, 'split': 'train', 'source_lineage': lineage,
            'reference': None,  # Independent operator labels are not yet available.
            'request': {'flag_id': flag_id, 'flag': {'category': category}, 'context': {
                'question': 'What needs operator attention for this %s event?' % category,
                'facts': facts, 'allowed_actions': actions, 'suggested_action': suggested,
                'citation_ids': [f['id'] for f in facts],
                'missing': [] if facts else ['event evidence unavailable']}}}
