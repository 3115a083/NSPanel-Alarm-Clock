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
            if name != self.target[1]:
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
        self.assertIn(b'prints "wa_clock_v1",0', preinit)
        self.assertNotIn(b'if(api==0)', preinit)

    def test_unknown_or_corrupt_source_is_refused(self):
        bad = bytearray(self.source)
        bad[-1] ^= 1
        with self.assertRaises(ValueError):
            MODULE.build(bytes(bad))


if __name__ == '__main__':
    unittest.main()
