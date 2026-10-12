"""Locate real host JVMs without requiring a private console-download cache."""
import os
from pathlib import Path
import unittest

REPO=Path(__file__).resolve().parents[2]

def runtime(major):
    homes=[Path(os.environ[key]) for key in (f'JAVA{major}_HOME',f'JAVA_HOME_{major}_X64') if os.environ.get(key)]
    if major==21:
        if os.environ.get('JAVA_HOME'):homes.append(Path(os.environ['JAVA_HOME']))
        homes.append(REPO/'.deps/host-jdk/jdk-21.0.8+9')
    if major==8:homes.append(REPO/'dist/PPSA99888/prosperomc/runtimes/java8')
    homes.append(REPO/f'artifacts/live-downloads/data/runtimes/java{major}')
    for home in homes:
        for suffix in ('java.exe','java'):
            candidate=home/'bin'/suffix
            if candidate.is_file():return candidate
    raise unittest.SkipTest(f'Java {major} host runtime required; set JAVA{major}_HOME')
