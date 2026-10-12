"""Exercise the real JNDI path and actual Minecraft redirect/address classes."""
import http.server
import json
import os
from pathlib import Path
import socketserver
import subprocess
import tempfile
import threading
import unittest
import urllib.parse
from tests.launcher.test_launcher import REPO,JAR,JAVAC,JAVA
from tests.launcher.test_dns import JAVA as JAVA8
from tests.launcher.runtimes import runtime as host_runtime

JAVA25=host_runtime(25)
JAVA17=host_runtime(17)


class ServerDnsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=REPO/'artifacts',prefix='server-dns-')
        cls.classes=Path(cls.temp.name)/'classes'
        subprocess.run([str(JAVAC),'--release','8','-encoding','UTF-8','-cp',str(JAR),'-d',str(cls.classes),
                        str(REPO/'tests/launcher/ServerDnsFixture.java')],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.hits=[];self.port=25566;test=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                args=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                name=args.get('name',[''])[0];record=args.get('type',[''])[0];test.hits.append((name,record))
                answer=[];status=0;truncated=False
                if 'missing' in name or name=='play.invalid':status=3
                elif 'empty' in name:pass
                elif record=='A':answer=[{'type':5,'data':'target.invalid'},{'type':1,'data':'127.0.0.1'}]
                elif record=='TXT':answer=[{'type':16,'data':'"example-value"'}]
                elif record=='SRV':
                    value='1 1 %d target.invalid.'%test.port
                    if 'bad-port' in name:value='1 1 65536 target.invalid.'
                    if 'bad-target' in name:value='1 1 25566 target/escape.invalid'
                    if 'disabled' in name:value='0 0 0 .'
                    if 'truncated' in name:truncated=True
                    if 'oversized' in name:value='x'*66000
                    answer=[{'type':33,'data':value}]
                data=json.dumps({'Status':status,'TC':truncated,'Answer':answer}).encode()
                self.send_response(200);self.end_headers();self.wfile.write(data)
            def log_message(*args):pass
        self.http=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=self.http.serve_forever,daemon=True).start()

    def tearDown(self):self.http.shutdown();self.http.server_close()

    def command(self,java,mode,extra=()):
        classpath=os.pathsep.join(map(str,[self.classes,JAR,*extra]))
        opens=['--add-opens=java.base/java.net=ALL-UNNAMED'] if java==JAVA17 else []
        return [str(java),*opens,'-Dprosperomc.ps5Dns=true','-Djava.net.preferIPv4Stack=true',
                '-Dprosperomc.dnsEndpoint=http://127.0.0.1:%d/dns-query'%self.http.server_port,
                '-cp',classpath,'org.prosperomc.ServerDnsFixture',mode]

    def test_hostname_and_directory_discovery_java8_17_21_25(self):
        for java in (JAVA8,JAVA17,JAVA,JAVA25):
            with self.subTest(java=java):
                result=subprocess.run(self.command(java,'directory'),capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('DIRECTORY_DNS_PASS',result.stdout)
        self.assertIn(('_minecraft._tcp.play.invalid','SRV'),self.hits)
        self.assertIn(('dialtone.invalid','TXT'),self.hits)

    def test_actual_minecraft_26_2_srv_ipv4_and_tcp_server_status(self):
        failures=[];requests=[]
        def varint(stream):
            value=0
            for shift in range(0,35,7):
                byte=stream.read(1)
                if not byte:raise EOFError('status connection closed')
                value|=(byte[0]&127)<<shift
                if not byte[0]&128:return value
            raise ValueError('bad VarInt')
        def encode(value):
            out=bytearray()
            while True:
                bits=value&127;value>>=7;out.append(bits|128 if value else bits)
                if not value:return bytes(out)
        class StatusHandler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    size=varint(self.rfile);packet=self.rfile.read(size)
                    requests.append(packet)
                    if self.rfile.read(2)!=b'\x01\x00':raise ValueError('client sent login instead of status')
                    data=json.dumps({'version':{'name':'26.2','protocol':0},'players':{'max':20,'online':0},
                                     'description':{'text':'Fixture server'}}).encode()
                    packet=b'\x00'+encode(len(data))+data
                    self.wfile.write(encode(len(packet))+packet);self.wfile.flush()
                except Exception as error:failures.append(str(error))
        status=socketserver.TCPServer(('127.0.0.1',0),StatusHandler)
        self.port=status.server_address[1]
        threading.Thread(target=status.serve_forever,daemon=True).start()
        try:
            client=REPO/'artifacts/storage-client/26.2.jar'
            libraries=list((REPO/'artifacts/live-downloads/data/libraries').rglob('*.jar'))
            if not client.is_file() or not libraries:
                self.skipTest('Optional actual Minecraft client/libraries not present; synthetic JNDI tests still run')
            self.assertTrue(client.is_file());self.assertTrue(libraries)
            # Mirror the earlier actual-client codec fixture's complete libraries.
            result=subprocess.run(self.command(JAVA25,'minecraft',[client,*libraries]),capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('ACTUAL_MINECRAFT_DNS_STATUS_PASS',result.stdout)
            self.assertEqual(failures,[]);self.assertEqual(len(requests),1)
            self.assertIn(b'target.invalid.',requests[0])
            self.assertIn(('_minecraft._tcp.play.invalid','SRV'),self.hits)
            self.assertIn(('target.invalid','A'),self.hits)
        finally:status.shutdown();status.server_close()
