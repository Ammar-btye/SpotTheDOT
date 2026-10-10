"""MemorySampler against a fake /sys/class/drm tree (plan 04-02). No GPU is read; nothing here is a measurement."""
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'amd/system2'))

from analyst.memory import DISABLED, MemorySampler  # noqa: E402

MIB = 1024 * 1024


def card(root: Path, name: str, vram=None, gtt=None, vendor='0x1002', device='0x1586'):
    d = root / name / 'device'
    d.mkdir(parents=True)
    if vram is not None:
        (d / 'mem_info_vram_used').write_text('%d\n' % vram)
    if gtt is not None:
        (d / 'mem_info_gtt_used').write_text('%d\n' % gtt)
    (d / 'vendor').write_text(vendor + '\n')
    (d / 'device').write_text(device + '\n')
    return d


def fake_root(tmp_path: Path) -> Path:
    root = tmp_path / 'drm'
    card(root, 'card0', 512 * MIB, 6000 * MIB)
    card(root, 'card2', 100 * MIB, 0, vendor='0x1002', device='0x7480')
    card(root, 'card0-DP-1', 999 * MIB, 999 * MIB)       # connector: ignored even with the files present
    card(root, 'card1')                                     # no mem_info files: ignored
    (root / 'renderD128').mkdir()
    return root


def test_sums_vram_and_gtt_across_cards_and_records_ids(tmp_path):
    s = MemorySampler(fake_root(tmp_path))
    total = s.sample()
    assert total == {'vram': 612 * MIB, 'gtt': 6000 * MIB, 'total': 6612 * MIB}
    result = s.stop()
    assert result['available'] is True and result['reason'] is None
    assert result['cards'] == [{'card': 'card0', 'vendor': '0x1002', 'device': '0x1586'},
                               {'card': 'card2', 'vendor': '0x1002', 'device': '0x7480'}]
    assert result['peak']['total_mib'] == 6612.0 and result['baseline']['vram_bytes'] == 612 * MIB


def test_baseline_is_first_sample_and_peak_is_max(tmp_path):
    root = fake_root(tmp_path)
    s = MemorySampler(root)
    s.sample()
    (root / 'card0/device/mem_info_gtt_used').write_text('%d' % (9000 * MIB))
    s.sample()
    (root / 'card0/device/mem_info_gtt_used').write_text('%d' % (100 * MIB))
    s.sample()
    result = s.stop()
    assert result['baseline']['total_mib'] == 6612.0
    assert result['peak']['gtt_mib'] == 9000.0 and result['peak']['total_bytes'] == (612 + 9000) * MIB
    assert result['samples'] == 4          # three explicit samples plus the final one in stop()


def test_thread_lifecycle_and_idempotent_stop(tmp_path):
    s = MemorySampler(fake_root(tmp_path), interval_s=0.01)
    with s:
        assert any(t.name == 'memory-sampler' for t in threading.enumerate())
    first = s.stop()
    assert s.stop() is first and isinstance(first, dict)
    assert not any(t.name == 'memory-sampler' and t.is_alive() for t in threading.enumerate())
    assert first['samples'] >= 2


def test_missing_or_empty_root_is_unavailable_not_an_error(tmp_path):
    for root in (tmp_path / 'absent', tmp_path):
        result = MemorySampler(root).start().stop()
        assert result['available'] is False and isinstance(result['reason'], str) and result['reason']
        assert result['peak'] is None and result['baseline'] is None and result['cards'] == []


def test_unreadable_values_are_skipped(tmp_path):
    root = tmp_path / 'drm'
    card(root, 'card0', 1, 1)
    (root / 'card0/device/mem_info_vram_used').write_text('garbage')
    assert MemorySampler(root).stop()['available'] is False


def test_disabled_sampler(tmp_path):
    result = MemorySampler(fake_root(tmp_path), enabled=False).start().stop()
    assert result['available'] is False and result['reason'] == DISABLED == \
        'memory sampling disabled (--mem-source none)'
    assert result['samples'] == 0
