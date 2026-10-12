import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from tests.launcher.test_launcher import REPO, JAR, JAVA, JAVAC

class FabricMetadataTests(unittest.TestCase):
    def test_installed_descriptors_match_actual_fabric_parser(self):
        loader=REPO/'artifacts/live-downloads/data/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar'
        corpus=REPO/'artifacts/fo-metadata-inspect'
        if not loader.is_file() or not corpus.is_dir():
            self.skipTest('Optional real Fabric loader/mod corpus not present; backend dependency fixtures still run')
        self.assertTrue(loader.is_file(), 'actual Fabric loader is required for compatibility validation')
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='fabric-metadata-') as temporary:
            folder=Path(temporary);classes=folder/'classes'
            cp=os.pathsep.join(map(str,[JAR,loader]))
            subprocess.run([str(JAVAC),'--release','8','-encoding','UTF-8','-cp',cp,'-d',str(classes),
                str(REPO/'tests/launcher/FabricMetadataFixture.java')],check=True,capture_output=True)
            result=subprocess.run([str(JAVA),'-cp',os.pathsep.join(map(str,[classes,JAR,loader])),
                'org.prosperomc.FabricMetadataFixture',str(corpus),str(folder)],text=True,capture_output=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('FABRIC_METADATA_PASS',result.stdout)
            print(result.stdout.strip())
