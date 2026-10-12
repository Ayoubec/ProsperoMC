"""Verify the game-directory alias against actual host filesystem identities."""
import base64
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from tests.launcher.test_launcher import REPO,JAR,JAVA,JAVAC

class GameStorageTests(unittest.TestCase):
    def test_data_drive_keeps_existing_world_and_save_destination(self):
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='storage-alias-check-') as temp:
            folder=Path(temp).resolve();assert folder.is_relative_to(REPO.resolve()/'artifacts')
            root=folder/'data';root.mkdir();wrong=folder/'wrong';wrong.mkdir();alias=folder/'alias'
            if os.name=='nt':
                command="New-Item -ItemType Junction -Path '"+str(alias).replace("'","''")+"' -Target '"+str(root).replace("'","''")+"' | Out-Null"
                encoded=base64.b64encode(command.encode('utf-16-le')).decode()
                subprocess.run(['powershell.exe','-NoProfile','-EncodedCommand',encoded],check=True,capture_output=True)
            else:alias.symlink_to(root,target_is_directory=True)
            assert alias.resolve().is_relative_to(folder)
            try:
                classes=folder/'classes'
                subprocess.run([str(JAVAC),'--release','8','-cp',str(JAR),'-d',str(classes),
                    str(REPO/'tests/launcher/GameStorageFixture.java')],check=True,capture_output=True)
                result=subprocess.run([str(JAVA),'-cp',os.pathsep.join(map(str,[classes,JAR])),
                    'org.prosperomc.GameStorageFixture',str(root),str(alias),str(wrong)],text=True,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('GAME_STORAGE_ALIAS_PASS',result.stdout)
                print(result.stdout.strip())
            finally:
                # Remove only the alias directory entry, never its target.
                if os.name=='nt':os.rmdir(alias)
                else:alias.unlink()

if __name__=='__main__':unittest.main()
