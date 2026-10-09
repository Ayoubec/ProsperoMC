#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('stage_ps5', ROOT / 'scripts/stage-ps5.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)

class StageTests(unittest.TestCase):
    def test_credentials_are_excluded_from_opt_in_minecraft_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'output'
            source.mkdir()
            (source / 'instance.cfg').write_text('name=Owned Minecraft')
            (source / 'Launcher_Accounts.json').write_text('{"token":"must-never-copy"}')
            (source / 'auth.json').write_text('{"accessToken":"must-never-copy"}')
            stage.copy_tree(source, target, filter_accounts=True)
            self.assertTrue((target / 'instance.cfg').is_file())
            self.assertEqual(sorted(item.name for item in target.iterdir()), ['instance.cfg'])

    def test_unexpected_credentials_reject_runtime_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'; source.mkdir()
            (source / 'accounts.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Credential'):
                stage.copy_tree(source, root / 'output')

    def test_partial_or_gdi_runtime_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'Missing'):
                stage.validate_wine(Path(temporary))
        # Inspect the actual downloaded, checksum-verified upstream release.
        release = ROOT / '.deps/releases/prospero-win-v0.1.1/PPSA99995'
        if release.is_dir():
            actual = stage.validate_wine(release)
            self.assertEqual(actual['sourceCommit'], stage.WINE_COMMIT)
            self.assertEqual(actual['opengl'], 'embedded in win32u.prx')

    def test_prefix_is_explicit_about_mismatched_host_wine(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source=root/'prefix'; source.mkdir()
            for name in ('system.reg','user.reg','userdef.reg'):
                (source/name).write_text('WINE REGISTRY Version 2\n')
            (source/'drive_c/windows/system32').mkdir(parents=True)
            (source/'prosperomc-prefix.json').write_text(json.dumps({'wineVersion':'wine-10.0'}))
            result=stage.stage_prefix(source,root/'output',root/'wine')
            self.assertFalse(result['matchingSource'])
            self.assertFalse(result['consoleValidated'])
            self.assertEqual((root/'output/dosdevices/.pw-symlinks').read_bytes(),b'c:\t../drive_c\nz:\t/\n')
            self.assertIn('"Audio"="ps5"',(root/'output/user.reg').read_text())

if __name__=='__main__':
    unittest.main()
