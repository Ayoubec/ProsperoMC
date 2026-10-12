"""Real classes/resources/services, conservative guards, and live handle savings."""
import ctypes
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.launcher.test_launcher import JAVA, JAVAC, JAR, REPO


class ClasspathCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(dir=REPO / "artifacts", prefix="classpath-cache-test-")
        cls.folder = Path(cls.temporary.name)
        cls.classes = cls.folder / "classes"
        subprocess.run([str(JAVAC), "--release", "8", "-cp", str(JAR), "-d", str(cls.classes),
                        str(REPO / "tests/launcher/ClasspathCacheFixture.java")], check=True, capture_output=True)
        cls.classpath = os.pathsep.join(map(str, [cls.classes, JAR]))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def command(self, mode):
        return [str(JAVA), "-cp", self.classpath, "org.prosperomc.ClasspathCacheFixture", mode,
                str(self.folder / mode)]

    def test_guards_cache_corruption_reuse_and_original_integrity(self):
        result = subprocess.run(self.command("safety"), text=True, capture_output=True, check=True)
        self.assertIn("PASS conservative guards", result.stdout)

    def test_independent_graphics_apis_preserve_options(self):
        result = subprocess.run(self.command("graphics"), text=True, capture_output=True, check=True)
        self.assertIn("PASS independent graphics APIs", result.stdout)

    def test_jar_resource_streams_release_archive_handles(self):
        original = self.measure("url-original")
        uncached = self.measure("url-uncached")
        retained = original["during"] - original["before"]
        released = uncached["during"] - uncached["before"]
        self.assertGreaterEqual(retained - released, 25, (original, uncached))
        print("JAR URL cache live-handle fixture:", {"original": original, "uncached": uncached,
                                                    "saved": retained - released})

    def measure(self, mode):
        process = subprocess.Popen(self.command(mode), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        handle = None
        if os.name == "nt":
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
            kernel.GetProcessHandleCount.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel.OpenProcess(0x1000, False, process.pid)
            self.assertTrue(handle)
        counts = {}
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                if line.startswith("MEASURE "):
                    if os.name == "nt":
                        value = ctypes.c_uint32()
                        self.assertTrue(kernel.GetProcessHandleCount(handle, ctypes.byref(value)))
                        total = value.value
                    else:
                        total = len(list((Path("/proc") / str(process.pid) / "fd").iterdir()))
                    counts[line.split()[1]] = total
                    process.stdin.write("\n")
                    process.stdin.flush()
            errors = process.stderr.read()
            self.assertEqual(process.wait(timeout=30), 0, errors)
            self.assertEqual(set(counts), {"before", "during", "after"})
            return counts
        finally:
            if handle:
                kernel.CloseHandle(handle)
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()

    def test_live_classloader_uses_fewer_file_handles_with_same_resources_and_services(self):
        original = self.measure("original")
        cached = self.measure("cached")
        jar_handles = original["during"] - original["before"]
        directory_handles = cached["during"] - cached["before"]
        self.assertGreaterEqual(jar_handles, 30, (original, cached))
        self.assertLessEqual(directory_handles, 12, (original, cached))
        self.assertGreaterEqual(jar_handles - directory_handles, 25, (original, cached))
        print("Classpath cache live-handle fixture:", {"original": original, "cached": cached,
                                                      "saved": jar_handles - directory_handles})


if __name__ == "__main__":
    unittest.main()
