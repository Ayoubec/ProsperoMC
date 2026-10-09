"""App-only publication preserves game data and rejects a corrupt transfer."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('patch_deploy',ROOT / 'scripts/deploy-ps5-patch.py')
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)

class FTP:
    def __init__(self,files,corrupt=False):
        self.files = dict(files)
        self.corrupt = corrupt
        self.writes = []
    def voidcmd(self,_): return '200'
    def size(self,name): return len(self.files[name])
    def storbinary(self,command,stream,**_):
        name = command[5:]
        self.files[name] = stream.read()
        if self.corrupt: self.files[name] = b'?'*len(self.files[name])
        self.writes.append(name)
    def retrbinary(self,command,collect): collect(self.files[command[5:]])
    def rename(self,before,after): self.files[after] = self.files.pop(before)

class AppUpdate(unittest.TestCase):
    def test_publish_preserves_world_and_skips_unchanged_binary(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'artifacts') as temp:
            source = Path(temp)
            assert source.resolve().is_relative_to(ROOT / 'artifacts')
            (source / 'app.txt').write_bytes(b'new app')
            (source / 'same.txt').write_bytes(b'same')
            ftp = FTP({'/data/ProsperoMC/world.dat':b'world-save',
                       '/data/ProsperoMC/same.txt':b'same'})
            manifest = {'same.txt':{'size':4,'sha256':hashlib.sha256(b'same').hexdigest()}}
            with patch.object(publish.deploy,'remote_inventory',return_value=manifest):
                publish.publish(ftp,'/data/ProsperoMC',source,['app.txt','same.txt'],True)
            self.assertEqual(ftp.files['/data/ProsperoMC/world.dat'],b'world-save')
            self.assertEqual(ftp.files['/data/ProsperoMC/app.txt'],b'new app')
            self.assertFalse(any('same.txt' in name for name in ftp.writes))
    def test_corrupt_upload_is_not_published(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'artifacts') as temp:
            source = Path(temp)
            assert source.resolve().is_relative_to(ROOT / 'artifacts')
            (source / 'app.txt').write_bytes(b'new app')
            ftp = FTP({'/title/app.txt':b'old app'},corrupt=True)
            with patch.object(publish.deploy,'remote_inventory',return_value={'existing':{}}):
                with self.assertRaisesRegex(ValueError,'hash mismatch'):
                    publish.publish(ftp,'/title',source,['app.txt'])
            self.assertEqual(ftp.files['/title/app.txt'],b'old app')

if __name__ == '__main__': unittest.main()
