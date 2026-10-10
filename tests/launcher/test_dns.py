"""Use the packaged Java 8 name-service API, with numeric HTTP DNS fixtures."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import threading
import unittest

REPO=Path(__file__).resolve().parents[2]
java8_home=Path(os.environ.get('JAVA8_HOME',os.environ.get('JAVA_HOME_8_X64',str(REPO/'dist/PPSA99888/prosperomc/runtimes/java8'))))
JAVA=next((p for p in (java8_home/'bin/java.exe',java8_home/'bin/java') if p.is_file()),java8_home/'bin/java')
jdk=Path(os.environ.get('JAVA_HOME',str(REPO/'.deps/host-jdk/jdk-21.0.8+9')))
JAVAC=next((p for p in (jdk/'bin/javac.exe',jdk/'bin/javac') if p.is_file()),Path(shutil.which('javac') or 'javac'))
JAR=REPO/'artifacts/launcher/prosperomc-launcher.jar'

class DnsTests(unittest.TestCase):
    def test_java8_service_resolves_aliases_rejects_bad_answers_and_keeps_loopback(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                good='good.invalid' in self.path
                self.send_response(200);self.end_headers()
                self.wfile.write(json.dumps({'Status':0,'Answer':[
                    {'type':5,'data':'alias.invalid'},
                    {'type':1,'data':'127.0.0.1' if good else '999.0.0.1'}]}).encode())
            def log_message(*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory(dir=REPO/'artifacts') as temporary:
                folder=Path(temporary)
                source=folder/'DnsCheck.java'
                source.write_text('''
import java.net.*;
import org.prosperomc.Ps5Dns;
public class DnsCheck {
 public static void main(String[] args)throws Exception {
  Ps5Dns.install(args[0]);
  if(!InetAddress.getByName("good.invalid").getHostAddress().equals("127.0.0.1"))throw new AssertionError();
  if(!InetAddress.getByName("localhost").isLoopbackAddress())throw new AssertionError();
  try { InetAddress.getByName("bad.invalid");throw new AssertionError("Invalid answer accepted"); }
  catch(UnknownHostException expected){}
  System.out.println("DNS_PASS");
 }
}''',encoding='utf-8')
                subprocess.run([str(JAVAC),'--release','8','-cp',str(JAR),'-d',str(folder),str(source)],check=True,capture_output=True)
                result=subprocess.run([str(JAVA),'-Djava.net.preferIPv4Stack=true','-cp',str(folder)+os.pathsep+str(JAR),
                    'DnsCheck','http://127.0.0.1:%d/dns-query'%server.server_port],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('DNS_PASS',result.stdout)
        finally:
            server.shutdown();server.server_close()
