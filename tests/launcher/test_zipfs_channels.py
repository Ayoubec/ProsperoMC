"""Real JDK ZIP filesystem backing pool on the host and packaged Java 25."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
import zipfile
from tests.launcher.test_launcher import REPO,JAR,JAVA,JAVAC
from tests.launcher.runtimes import runtime as host_runtime

class ZipFsChannelsTests(unittest.TestCase):
    def test_signed_jars_keep_verification_after_eviction(self):
        bootstrap=JAR.with_name('prosperomc-zipfs.jar')
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='signed-pool-check-') as temp:
            folder=Path(temp);classes=folder/'classes'
            with zipfile.ZipFile(folder/'signed.jar','w') as archive:archive.writestr('data.txt','signed content')
            keytool=JAVAC.with_name('keytool.exe' if os.name=='nt' else 'keytool')
            signer=JAVAC.with_name('jarsigner.exe' if os.name=='nt' else 'jarsigner')
            subprocess.run([str(keytool),'-genkeypair','-alias','fixture','-keystore',str(folder/'fixture.p12'),
                '-storepass','fixture-password','-keypass','fixture-password','-keyalg','RSA','-keysize','2048',
                '-dname','CN=Archive Fixture','-validity','2','-noprompt'],check=True,capture_output=True)
            subprocess.run([str(signer),'-keystore',str(folder/'fixture.p12'),'-storepass','fixture-password',
                str(folder/'signed.jar'),'fixture'],check=True,capture_output=True)
            with zipfile.ZipFile(folder/'signed.jar') as source,zipfile.ZipFile(folder/'corrupt.jar','w') as corrupt:
                for entry in source.infolist():corrupt.writestr(entry,b'altered' if entry.filename=='data.txt' else source.read(entry))
            subprocess.run([str(JAVAC),'--release','8','-cp',str(bootstrap),'-d',str(classes),
                str(REPO/'tests/launcher/SignedArchiveFixture.java')],check=True,capture_output=True)
            candidates=[JAVA]
            modern=host_runtime(25)
            if modern.is_file():candidates.append(modern)
            for java in candidates:
                result=subprocess.run([str(java),'-javaagent:'+str(JAR)+'='+str(bootstrap),'-cp',
                    os.pathsep.join(map(str,[classes,bootstrap])),'SignedArchiveFixture',str(folder)],
                    text=True,capture_output=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('SIGNED_JAR_POOL_PASS',result.stdout)
                print(result.stdout.strip())
                for copied in folder.glob('signed-*.jar'):copied.unlink()

    def test_real_zipfs_reads_writes_eviction_and_concurrency(self):
        bootstrap=JAR.with_name('prosperomc-zipfs.jar')
        self.assertTrue(bootstrap.is_file())
        candidates=[JAVA]
        modern=host_runtime(25)
        if modern.is_file() and modern.resolve()!=JAVA.resolve():candidates.append(modern)
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='zipfs-live-check-') as temp:
            folder=Path(temp);classes=folder/'classes'
            subprocess.run([str(JAVAC),'--release','8','-cp',str(bootstrap),'-d',str(classes),
                            str(REPO/'tests/launcher/ZipFsChannelsFixture.java')],check=True,capture_output=True)
            for number,java in enumerate(candidates):
                with self.subTest(java=str(java)):
                    result=subprocess.run([str(java),'-javaagent:'+str(JAR)+'='+str(bootstrap),
                        '-cp',os.pathsep.join(map(str,[classes,bootstrap])),'ZipFsChannelsFixture',str(folder/str(number))],
                        text=True,capture_output=True,timeout=120)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertIn('ZIPFS_CHANNELS_PASS',result.stdout)
                    print(result.stdout.strip())

if __name__=='__main__':unittest.main()
