"""Reproduce PS5's adapter Error in the real pinned Netty initializer."""
from pathlib import Path
import os
import struct
import subprocess
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'game-data/prosperomc/libraries/io/netty/netty-all/4.1.9.Final/netty-all-4.1.9.Final.jar'
JDK=ROOT/'.deps/host-jdk/jdk-21.0.8+9/bin'
JAVA=ROOT/'dist/PPSA99888/prosperomc/runtimes/java8/bin/java.exe'
JAR=ROOT/'artifacts/launcher/prosperomc-launcher.jar'
ENTRY='io/netty/util/NetUtil.class'

def adapter_error_fixture(data):
    count=struct.unpack_from('>H',data,8)[0]
    parts=[None]*count;strings={};classes={};names={};position=10;i=1
    sizes={3:4,4:4,5:8,6:8,7:2,8:2,9:4,10:4,11:4,12:4,15:3,16:2,18:4}
    while i<count:
        start=position;tag=data[position];position+=1
        if tag==1:
            size=struct.unpack_from('>H',data,position)[0]
            strings[i]=data[position+2:position+2+size].decode('utf-8',errors='replace')
            position+=2+size
        else:
            if tag==7:classes[i]=struct.unpack_from('>H',data,position)[0]
            if tag==12:names[i]=struct.unpack_from('>H',data,position)[0]
            position+=sizes[tag]
        parts[i]=data[start:position]
        i+=2 if tag in (5,6) else 1
    modified=0
    for i,entry in enumerate(parts):
        if entry and entry[0]==10:
            owner,method=struct.unpack_from('>HH',entry,1)
            if strings[classes[owner]]=='java/net/NetworkInterface' and strings[names[method]]=='getNetworkInterfaces':
                parts[i]=b'\x0a'+struct.pack('>HH',count+1,method);modified+=1
    assert modified==1
    mock=b'org/prosperomc/MockNetworkInterfaces'
    append=b'\x01'+struct.pack('>H',len(mock))+mock+b'\x07'+struct.pack('>H',count)
    return data[:8]+struct.pack('>H',count+2)+b''.join(p for p in parts if p)+append+data[position:]

@unittest.skipUnless(LIB.exists() and JAVA.exists(),'Requires local pinned Netty and Java 8 test runtime')
class NettyCompatibility(unittest.TestCase):
    def test_real_netty_adapter_error_and_tcp_listener(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as temporary:
            work=Path(temporary);classes=work/'classes';classes.mkdir()
            cp=os.pathsep.join(map(str,[JAR,LIB,classes]))
            subprocess.run([JDK/'javac.exe','--release','8','-cp',cp,'-d',classes,
                ROOT/'tests/runtime/NettySmoke.java',ROOT/'tests/runtime/MockNetworkInterfaces.java'],check=True,capture_output=True)
            prepared=subprocess.run([JAVA,'-cp',cp,'org.prosperomc.NettySmoke',work,LIB],check=True,capture_output=True,text=True)
            overlay=Path(prepared.stdout.strip())
            with zipfile.ZipFile(LIB) as original,zipfile.ZipFile(overlay) as patched:
                self.assertIn('META-INF/LICENSE.txt',patched.namelist())
                for name,data in [('before',original.read(ENTRY)),('after',patched.read(ENTRY))]:
                    fixture=work/(name+'.jar')
                    with zipfile.ZipFile(fixture,'w') as out:out.writestr(ENTRY,adapter_error_fixture(data))
                    tested=subprocess.run([JAVA,'-cp',os.pathsep.join(map(str,[fixture,classes,JAR,LIB])),
                        'org.prosperomc.NettySmoke'],capture_output=True,text=True,timeout=20)
                    if name=='before':
                        self.assertNotEqual(tested.returncode,0)
                        self.assertIn('GetIfTable function failed',tested.stderr)
                    else:
                        self.assertEqual(tested.returncode,0,tested.stdout+tested.stderr)
                        self.assertIn('TCP request/reply',tested.stdout)

if __name__=='__main__':unittest.main()
