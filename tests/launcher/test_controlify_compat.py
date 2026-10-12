"""Check scoped controller identity using the installed mod and client metadata."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile
from tests.launcher.test_launcher import REPO,JAR,JAVA,JAVAC,zipped
from tests.launcher.runtimes import runtime as host_runtime

class ControlifyCompatTests(unittest.TestCase):
    def test_generated_pack_with_actual_minecraft_codec(self):
        client=REPO/'artifacts/storage-client/26.2.jar'
        mod=REPO/'artifacts/controlify-inspect/controlify-3.5.0+mc26.2-universal.jar'
        if not all(path.is_file() for path in (client,mod)) or not (REPO/'artifacts/fo-metadata-inspect/controller-pack.mcmeta').is_file():
            self.skipTest('Optional actual Minecraft/Controlify codec corpus not present; scoped synthetic controller test still runs')
        java25=host_runtime(25)
        original=REPO/'artifacts/fo-metadata-inspect/controller-pack.mcmeta'
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='pack-codec-') as temp:
            folder=Path(temp);classes=folder/'classes'
            subprocess.run([str(JAVAC),'--release','8','-cp',str(JAR),'-d',str(classes),
                str(REPO/'tests/launcher/PackMetadataCodecFixture.java')],check=True,capture_output=True)
            libraries=list((REPO/'artifacts/live-downloads/data/libraries').rglob('*.jar'))
            cp=os.pathsep.join(map(str,[classes,JAR,client]+libraries))
            argfile=folder/'java.args'
            argfile.write_text('-cp\n"'+cp.replace('\\','/')+'"\norg.prosperomc.PackMetadataCodecFixture\n'+
                '\n'.join('"'+str(p).replace('\\','/')+'"' for p in [folder,client,mod,original]),encoding='utf-8')
            result=subprocess.run([str(java25),'@'+str(argfile)],text=True,capture_output=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('PACK_METADATA_CODEC_PASS',result.stdout)
            print(result.stdout.strip())

    def test_controller_identity_preserves_packs_and_control_settings(self):
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='controlify-compat-') as temp:
            folder=Path(temp);classes=folder/'classes'
            mod=REPO/'artifacts/controlify-inspect/controlify-3.5.0+mc26.2-universal.jar'
            client=REPO/'artifacts/storage-client/26.2.jar'
            if not mod.is_file():
                mod=folder/'controlify.jar';mod.write_bytes(zipped({
                    'assets/controlify/controllers/controller_identification.json5':'[]',
                    'assets/controlify/controllers/font_mappings/dualsense.json':'{}',
                    'dev/isxander/controlify/controller/id/ControllerTypeManager.class':'getResourceStack'}))
            if not client.is_file():
                client=folder/'client.jar';client.write_bytes(zipped({'version.json':'{"pack_version":{"resource_major":88,"resource_minor":0}}'}))
            subprocess.run([str(JAVAC),'--release','8','-cp',str(JAR),'-d',str(classes),
                str(REPO/'tests/launcher/ControlifyCompatFixture.java')],check=True,capture_output=True)
            result=subprocess.run([str(JAVA),'-cp',os.pathsep.join(map(str,[classes,JAR])),
                'org.prosperomc.ControlifyCompatFixture',str(folder),str(client),str(mod)],
                text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('CONTROLIFY_COMPAT_PASS',result.stdout)
            print(result.stdout.strip())

if __name__=='__main__':unittest.main()
