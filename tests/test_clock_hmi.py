"""Check the actual pinned HMI transformation, including unchanged other resources."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('clock_hmi', ROOT / 'tools/build_clock_hmi.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ClockHmiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / 'build/tft/upstream/nspanel_landscape.hmi'
        if not source.exists():
            raise RuntimeError('Run python tools/prepare_tft_sources.py before tests')
        cls.source = source.read_bytes()
        cls.result = MODULE.build(cls.source)
        cls.entries = MODULE.directory(cls.result)
        cls.target = next(e for e in cls.entries if e[1].endswith('.pa') and
            cls.result[e[2]+24:e[2]+40].split(b'\0')[0] == b'home_smpl')
        _, _, start, size = cls.target
        cls.components = MODULE.read_page(cls.result[start:start+size])

    def test_every_other_live_resource_is_byte_identical(self):
        before = {name: self.source[start:start+size] for _, name, start, size in MODULE.directory(self.source)}
        after = {name: self.result[start:start+size] for _, name, start, size in self.entries}
        self.assertEqual(set(before), set(after))
        for name, data in before.items():
            if name != self.target[1] and not (name.endswith('.pa') and data[24:40].split(b'\0')[0] == b'boot'):
                with self.subTest(resource=name):
                    self.assertEqual(data, after[name])

    def test_legacy_component_names_ids_and_count_are_preserved(self):
        self.assertEqual(len(self.components), 22+len(MODULE.LAYOUT))
        for index, component in enumerate(self.components):
            self.assertEqual(int.from_bytes(MODULE.attribute(component,'id'),'little'), index)
        self.assertEqual(MODULE.attribute(self.components[0],'objname'), b'home_smpl')
        self.assertEqual([MODULE.attribute(c,'objname').decode() for c in self.components[22:]],
            [row[0] for row in MODULE.LAYOUT])

    def test_clock_view_has_no_old_touch_navigation_or_running_timers(self):
        for component in self.components:
            for name, lines in component.items():
                if name.startswith(b'codes') and name != b'codesload':
                    self.assertEqual(lines, [])
            if int.from_bytes(MODULE.attribute(component,'type'),'little') == 51:
                self.assertEqual(MODULE.attribute(component,'en'), b'\0')
        preinit = self.components[0][b'codesload']
        self.assertIn(b'prints "wa_clock_v2",0', preinit)
        self.assertNotIn(b'if(api==0)', preinit)

    def test_new_text_rectangles_do_not_overlap(self):
        # The full-page opaque background deliberately covers legacy widgets.
        rows = MODULE.LAYOUT[1:]
        for i, a in enumerate(rows):
            for b in rows[i+1:]:
                overlap = a[2] < b[2]+b[4] and b[2] < a[2]+a[4] and a[3] < b[3]+b[5] and b[3] < a[3]+a[5]
                self.assertFalse(overlap, (a[0], b[0]))

    def test_boot_protocol_announcement_preserves_original_events(self):
        before = next(e for e in MODULE.directory(self.source) if e[1].endswith('.pa') and
            self.source[e[2]+24:e[2]+40].split(b'\0')[0] == b'boot')
        after = next(e for e in self.entries if e[1] == before[1])
        old = MODULE.read_page(self.source[before[2]:before[2]+before[3]])
        new = MODULE.read_page(self.result[after[2]:after[2]+after[3]])
        self.assertEqual(len(old), len(new))
        for a, b in zip(old, new):
            if MODULE.attribute(a, 'objname') == b'tm_display_ack':
                self.assertEqual(b[b'codestimer'][:len(a[b'codestimer'])], a[b'codestimer'])
                self.assertEqual(b[b'codestimer'][len(a[b'codestimer']):],
                    [b'printh 93', b'prints "wa_hmi_v2",0', b'printh 00 01 FF FF FF'])
                b = {**b, b'codestimer': a[b'codestimer']}
            self.assertEqual(a, b)

    def test_unknown_or_corrupt_source_is_refused(self):
        bad = bytearray(self.source)
        bad[-1] ^= 1
        with self.assertRaises(ValueError):
            MODULE.build(bytes(bad))


if __name__ == '__main__':
    unittest.main()
