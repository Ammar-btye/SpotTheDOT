"""Fail-closed offline saved-case approval against checked-in kit sources.

Kit rows come from paths.kit_dir() (SPOT_KIT_DIR or the checked-in kit), the same source the grounding entity catalog
uses; a different kit fails the row-hash checks. Static passages and the seed export need the repository checkout.

Two splits, never mixed. 'train' (the default everywhere, so prompts.load_examples can never read anything else)
accepts only training missions and rejects any holdout row. 'heldout' accepts only System 1 fold-2 missions, and every
dynamic row must come from the case's own mission at or before as_of (no evidence crosses missions); static asset and
location rows stay allowed. heldout_dataset() builds the Phase 4 headline set deterministically from the kit and the
checked-in policy; its manifest carries split 'heldout' and HELDOUT_POLICY_VERSION, the train manifest is unchanged.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .backend_contract import BackendAssessRequest
from .packet import normalize_packet
from .paths import kit_dir, repo_root
POLICY_VERSION = 'saved-kit-fold2-asof-v1'
HELDOUT_POLICY_VERSION = 'saved-kit-fold2-heldout-asof-v1'
SPLITS = ('train', 'heldout')
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


def _repo() -> Path:
    root = repo_root()
    if root is None:
        raise ValueError('repository checkout required (static passages, seed export)')
    return root


def source_tables() -> dict:
    kit, tables = kit_dir(), {}
    try:
        for table, key in KEYS.items():
            with (kit / (table + '.csv')).open(encoding='utf-8', newline='') as stream:
                tables[table] = {r[key]: r for r in csv.DictReader(stream)}
    except OSError as exc:
        raise ValueError('kit source tables unavailable') from exc
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


def _split(split) -> str:
    if split not in SPLITS:
        raise ValueError('unknown split %r' % (split,))
    return split


def _checked_rows(provenance, as_of, tables, split='train', mission_id=None):
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
        if _split(split) == 'train' and row.get('mission_id') in HOLDOUT_MISSIONS:
            raise ValueError('holdout source row prohibited')
        if split == 'heldout' and availability(table, row) is not None and row.get('mission_id') != mission_id:
            raise ValueError('held-out dynamic evidence must come from the case mission only')
        if ref != source_ref(table, row):
            raise ValueError('source hash or availability does not match source row')
        static = availability(table, row) is None
        if provenance['kind'] != ('static' if static else 'dynamic'):
            raise ValueError('provenance kind does not match source')
        if not static and _time(ref['available_at']) > as_of:
            raise ValueError('evidence not available at as_of')
        checked.append((table, row))
    return checked


def _check_item(item, as_of, tables, split='train', mission_id=None):
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
        try:
            source = (_repo() / provenance['path']).read_bytes()
        except OSError as exc:
            raise ValueError('static passage source unavailable') from exc
        if hashlib.sha256(source).hexdigest() != provenance['source_hash'] or not isinstance(item['text'], str) or not item['text'].strip() or item['text'] not in source.decode('utf-8'):
            raise ValueError('static passage does not match source')
    else:
        if set(item) != {'id', 'fact', 'provenance'}:
            raise ValueError('unsupported evidence fields or uncertified aggregate')
        rows = _checked_rows(provenance, as_of, tables, split, mission_id)
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


def validate_dataset(value, split: str = 'train') -> tuple[SavedCase, ...]:
    _split(split)
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
        if record['category'] not in CATEGORIES or record['split'] != split:
            raise ValueError('only controlled %s categories accepted' % split)
        if record['mission_id'] not in tables['missions'] or (record['mission_id'] in HOLDOUT_MISSIONS) != (
                split == 'heldout'):
            raise ValueError('case must belong to a real %s mission' % split)
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
                _check_item(item, as_of, tables, split, record['mission_id'])
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
        if record['category'] != 'insufficient_context' and prepared.insufficient_context:
            # else the harness silently moves it out of the sufficient denominators while it keeps its label
            raise ValueError('case category does not match packet sufficiency')
        cases.append(SavedCase(record['case_id'], record['category'], record['mission_id'], record['as_of'],
                               record['split'], canonical_bytes(request), canonical_bytes(lineage),
                               canonical_bytes(record.get('reference'))))
    result = tuple(sorted(cases, key=lambda c: c.case_id))
    if 'manifest' in value and value['manifest'] != dataset_manifest(result):
        raise ValueError('dataset manifest mismatch')
    return result


def dataset_manifest(cases) -> dict:
    """Train manifests are exactly the Phase 2 shape; held-out ones add split 'heldout' (also inside the hash)."""
    rows = [c.to_dict() for c in sorted(cases, key=lambda c: c.case_id)]
    splits = {c.split for c in cases}
    if len(splits) > 1:
        raise ValueError('a dataset must not mix splits')
    heldout = splits == {'heldout'}
    head = {'policy_version': HELDOUT_POLICY_VERSION if heldout else POLICY_VERSION, 'holdout_fold': 2,
            'holdout_missions': sorted(HOLDOUT_MISSIONS)}
    if heldout:
        head['split'] = 'heldout'
    return {**head, 'case_count': len(rows), 'content_hash': content_hash({**head, 'cases': rows})}


def load_dataset(path: str | Path, split: str = 'train') -> tuple[SavedCase, ...]:
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('cannot read saved dataset') from exc
    return validate_dataset(value, split)


def _system1():
    """system1 kit/events/policy and the MCP domain, guarded to the checked-in policy (no environment override)."""
    import sys
    root = _repo()
    sys.path.insert(0, str(root / 'amd/system1'))
    sys.path.insert(0, str(root / 'amd/mcp'))
    from triage import events, policy
    from triage.kit import load_kit
    from spot_mcp import domain

    if domain._POLICY_PATH.resolve() != (root / 'amd/system1/triage/policy.py').resolve():
        raise ValueError('seed export requires the checked-in policy, not an environment override')
    return load_kit(kit_dir()), events, policy, domain


def _action_facts(tables, action_id):
    """F1 = the action row, then its readings and anomalies in key order (individual rows, never aggregates)."""
    facts = [evidence_item('F1', 'actions', tables['actions'][action_id])]
    for table in ('readings', 'anomalies'):
        matches = [r for r in tables[table].values() if r['action_id'] == action_id]
        for source in sorted(matches, key=lambda r: r[KEYS[table]]):
            facts.append(evidence_item('F%d' % (len(facts) + 1), table, source))
    return facts


def _suggested(kit, domain, action, category, priority):
    action_facts = {**action, **(kit.anomalies.get(action['action_id']) or {}),
                    'environment': kit.locations[action['location_id']]['environment']}
    return domain.suggested_action(category, priority, action_facts)


def seed_dataset() -> dict:
    """Deterministic offline export, separate from backend's runtime retrieval."""
    kit, events, policy, domain = _system1()
    action_event, label_action = events.action_event, policy.label_action
    tables = source_tables()
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
        facts = _action_facts(tables, action['action_id'])
        as_of = max(r['available_at'] for f in facts for r in f['provenance']['source_rows'])
        suggested = _suggested(kit, domain, action, category, labelled['priority'])
        records.append(_seed_record(index, category, action['mission_id'], as_of, facts,
                                    vocabulary[category], suggested))
    mission = next(r for key, r in sorted(tables['missions'].items()) if key not in HOLDOUT_MISSIONS)
    records.append(_seed_record(5, 'mission', mission['mission_id'], mission['end_time'],
                               [evidence_item('F1', 'missions', mission)], vocabulary['mission'], 'REVIEW_MISSION'))
    records.append(_seed_record(6, 'insufficient_context', mission['mission_id'], mission['start_time'], [],
                               {'MANUAL_REVIEW': 'request operator review'}, 'MANUAL_REVIEW'))
    cases = validate_dataset({'cases': records})
    return {'cases': [c.to_dict() for c in cases], 'manifest': dataset_manifest(cases)}


def heldout_dataset() -> dict:
    """Controlled fold-2 held-out packets: the events System 2 can actually be asked to explain.

    Population (checked-in policy): one case per fold-2 action whose label_action category is not 'none' (P1-P3;
    Laya can raise a P3 to an escalation in parallel mode, so every flagged action is explainable), and one case per
    fold-2 mission whose label_mission priority is not P4. Evidence is individual kit rows of the case's own mission
    available at as_of: an action case cites its action row as F1, then its readings and anomalies; a mission case
    cites the mission row, its anomaly rows by anomaly_id, then its FAILED action rows by action_id, as of end_time.
    reference stays None: human labels are out of scope (04-CONTEXT), so no reference is ever invented.
    """
    kit, events, policy, domain = _system1()
    tables = source_tables()
    vocabulary = domain.ALLOWED_ACTIONS
    specs = []    # (case_id, category, mission_id, as_of, facts, suggested)
    for action in kit.actions:
        if action['mission_id'] not in HOLDOUT_MISSIONS:
            continue
        event = events.action_event(action, kit.missions[action['mission_id']], kit.locations[action['location_id']],
                                    kit.assets[action['asset_id']], kit.readings.get(action['action_id']),
                                    kit.anomalies.get(action['action_id']), 'kit')
        labelled = policy.label_action(event)
        category = labelled['category']
        if category == 'none':
            continue
        facts = _action_facts(tables, action['action_id'])
        as_of = max(r['available_at'] for f in facts for r in f['provenance']['source_rows'])
        specs.append(('heldout-' + action['action_id'], category, action['mission_id'], as_of, facts,
                      _suggested(kit, domain, action, category, labelled['priority'])))
    for mission_id in sorted(HOLDOUT_MISSIONS):
        mission = kit.missions[mission_id]
        actions = sorted(kit.actions_of(mission_id), key=lambda a: (a['timestamp'], a['sequence']))
        last = events.mission_events(mission, actions, kit.locations, kit.assets, kit.readings, kit.anomalies,
                                     'kit')[-1]
        if policy.label_mission(last)['priority'] == 'P4':
            continue
        rows = [('missions', tables['missions'][mission_id])]
        rows += [('anomalies', r) for _, r in sorted(tables['anomalies'].items()) if r['mission_id'] == mission_id]
        rows += [('actions', r) for _, r in sorted(tables['actions'].items())
                 if r['mission_id'] == mission_id and r['status'] == 'FAILED']
        facts = [evidence_item('F%d' % i, table, row) for i, (table, row) in enumerate(rows, 1)]
        specs.append(('heldout-mission-' + mission_id, 'mission', mission_id, rows[0][1]['end_time'], facts,
                      'REVIEW_MISSION'))
    records = [_record(case_id, 1000 + index, category, mission_id, as_of, facts, vocabulary[category], suggested,
                       'heldout')
               for index, (case_id, category, mission_id, as_of, facts, suggested) in enumerate(sorted(specs), 1)]
    cases = validate_dataset({'cases': records}, split='heldout')
    return {'cases': [c.to_dict() for c in cases], 'manifest': dataset_manifest(cases)}


def _seed_record(flag_id, category, mission_id, as_of, facts, actions, suggested):
    return _record('kit-' + category, flag_id, category, mission_id, as_of, facts, actions, suggested, 'train')


def _record(case_id, flag_id, category, mission_id, as_of, facts, actions, suggested, split):
    lineage = [r for f in facts for r in f['provenance']['source_rows']]
    return {'case_id': case_id, 'category': category, 'mission_id': mission_id,
            'as_of': as_of, 'split': split, 'source_lineage': lineage,
            'reference': None,  # Independent operator labels are not yet available.
            'request': {'flag_id': flag_id, 'flag': {'category': category}, 'context': {
                'question': 'What needs operator attention for this %s event?' % category,
                'facts': facts, 'allowed_actions': actions, 'suggested_action': suggested,
                'citation_ids': [f['id'] for f in facts],
                'missing': [] if facts else ['event evidence unavailable']}}}
