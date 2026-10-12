import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from tests.launcher.test_launcher import REPO,JAR,JAVA,JAVAC
from tests.launcher.runtimes import runtime as host_runtime

class GameplayProfileTests(unittest.TestCase):
    def test_selective_bounded_one_shot_recording_actual_runtimes(self):
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='gameplay-profile-') as temporary:
            base=Path(temporary);classes=base/'classes'
            subprocess.run([str(JAVAC),'--release','17','-cp',str(JAR),'-d',str(classes),
                str(REPO/'tests/launcher/GameplayProfileFixture.java'),
                str(REPO/'scripts/GameplayProfileAnalysis.java')],check=True,capture_output=True)
            runtimes=[host_runtime(17),JAVA,host_runtime(25)]
            for index,runtime in enumerate(runtimes):
                result=subprocess.run([str(runtime),'-cp',os.pathsep.join(map(str,[classes,JAR])),
                    'org.prosperomc.GameplayProfileFixture',str(base/str(index))],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('GAMEPLAY_PROFILE_PASS',result.stdout);print(result.stdout.strip())

    def test_java8_keeps_game_launch_and_request_without_initializing_jfr(self):
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='legacy-profile-') as temporary:
            base=Path(temporary);classes=base/'classes'
            subprocess.run([str(JAVAC),'--release','8','-cp',str(JAR),'-d',str(classes),
                str(REPO/'tests/launcher/GameplayProfileLegacyFixture.java')],check=True,capture_output=True)
            runtime=host_runtime(8)
            result=subprocess.run([str(runtime),'-cp',os.pathsep.join(map(str,[classes,JAR])),
                'org.prosperomc.GameplayProfileLegacyFixture',str(base/'data')],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('GAMEPLAY_PROFILE_LEGACY_PASS',result.stdout);print(result.stdout.strip())
