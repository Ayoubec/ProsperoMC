import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from tests.launcher.test_launcher import REPO,JAR,JAVA,JAVAC
from tests.launcher.runtimes import runtime as host_runtime

class StartupDiagnosticsTests(unittest.TestCase):
    def test_java25_code_cache_policy_retains_reclamation_and_budget(self):
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='code-cache-policy-') as temporary:
            classes=Path(temporary)/'classes'
            subprocess.run([str(JAVAC),'--release','8','-cp',str(JAR),'-d',str(classes),
                str(REPO/'tests/launcher/CodeCachePolicyFixture.java')],check=True,capture_output=True)
            runtime=host_runtime(25)
            command=[str(runtime),'-cp',os.pathsep.join(map(str,[classes,JAR])),'org.prosperomc.CodeCachePolicyFixture']
            flags=subprocess.run(command+['arguments'],check=True,capture_output=True,text=True).stdout.splitlines()
            result=subprocess.run([str(runtime),*flags,'-XX:+UseParallelGC','-Xmx512M',*command[1:]],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('CODE_CACHE_POLICY_PASS',result.stdout);print(result.stdout.strip())
    def test_configured_heap_and_collector_estimate_are_distinct(self):
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='heap-budget-') as temporary:
            classes=Path(temporary)/'classes'
            subprocess.run([str(JAVAC),'--release','8','-cp',str(JAR),'-d',str(classes),
                str(REPO/'tests/launcher/HeapBudgetFixture.java')],check=True,capture_output=True)
            for runtime in (JAVA,host_runtime(25)):
                result=subprocess.run([str(runtime),'-Xms512M','-Xmx4096M','-XX:+UseParallelGC',
                    '-XX:-UseCompressedOops','-XX:-UseCompressedClassPointers',
                    '-cp',os.pathsep.join(map(str,[classes,JAR])),'org.prosperomc.HeapBudgetFixture'],
                    text=True,capture_output=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('configured=4096M',result.stdout)
                self.assertIn('reportedMiB=3641',result.stdout)
                self.assertIn('HEAP_BUDGET_RESERVE_PASS',result.stdout)
                print(result.stdout.strip())
    def test_relocated_render_thread_is_sampled(self):
        with tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='render-sample-') as temporary:
            folder=Path(temporary);classes=folder/'classes'
            subprocess.run([str(JAVAC),'--release','8','-cp',str(JAR),'-d',str(classes),
                str(REPO/'tests/launcher/StartupDiagnosticsFixture.java')],check=True,capture_output=True)
            runtimes=[JAVA,host_runtime(25)]
            for runtime in runtimes:
                result=subprocess.run([str(runtime),'-XX:+UseParallelGC',
                    '-XX:ReservedCodeCacheSize=384M','-XX:MetaspaceSize=128M',
                    '-Xlog:gc,safepoint=info,codecache=info',
                    '-cp',os.pathsep.join(map(str,[classes,JAR])),'org.prosperomc.StartupDiagnosticsFixture'],
                    text=True,capture_output=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('STARTUP_RENDER_THREAD_PASS',result.stdout)
                self.assertIn('[gc]',result.stdout)
                self.assertIn('[safepoint]',result.stdout)
                print(result.stdout.strip())
