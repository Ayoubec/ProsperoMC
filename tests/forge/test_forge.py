"""Real Java helper tests with isolated HTTP and installer ZIP fixtures."""
import hashlib
import http.server
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
import zipfile

REPO=Path(__file__).resolve().parents[2]
JDK=REPO/'.deps/host-jdk/jdk-21.0.8+9/bin'
CLASSES=REPO/'artifacts/forge/testclasses'
VERSION='14.23.5.2864'
COORD='net.minecraftforge:forge:1.12.2-'+VERSION
REL='net/minecraftforge/forge/1.12.2-'+VERSION+'/forge-1.12.2-'+VERSION+'.jar'

def archive(entries):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for name,data in entries.items(): z.writestr(name,data)
    return out.getvalue()

class ForgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CLASSES.mkdir(parents=True,exist_ok=True)
        sources=list((REPO/'launcher/src').rglob('*.java'))+[REPO/'tests/forge/ForgeProbe.java']
        subprocess.run([str(JDK/'javac.exe'),'--release','8','-encoding','UTF-8','-d',str(CLASSES)]+list(map(str,sources)),check=True,capture_output=True)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=REPO/'artifacts/forge')
        self.dir=Path(self.temp.name);self.root=self.dir/'data';self.blobs={}
        blobs=self.blobs
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(h):
                if h.path not in blobs: h.send_error(404);return
                h.send_response(200);h.end_headers();h.wfile.write(blobs[h.path])
            def log_message(*args): pass
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:%d'%self.server.server_port
        self.forge=archive({'net/minecraftforge/Fixture.class':b'fixture'})
        self.lib=archive({'library.class':b'fixture library'})
        self.blobs['/library.jar']=self.lib
        self.spec={'path':REL,'url':'','sha1':hashlib.sha1(self.forge).hexdigest(),'size':len(self.forge)}
        self.patch={'id':'1.12.2-forge-'+VERSION,'inheritsFrom':'1.12.2','mainClass':'net.minecraft.launchwrapper.Launch',
                    'minecraftArguments':'--username ${auth_player_name} --tweakClass net.minecraftforge.fml.common.launcher.FMLTweaker',
                    'libraries':[{'name':COORD,'downloads':{'artifact':self.spec}},
                                 {'name':'fixture:lib:2','downloads':{'artifact':{'path':'fixture/lib/2/lib-2.jar','url':self.url+'/library.jar','sha1':hashlib.sha1(self.lib).hexdigest(),'size':len(self.lib)}}}]}
        self.base={'id':'1.12.2','mainClass':'net.minecraft.client.main.Main','javaVersion':{'majorVersion':8},
                   'downloads':{'client':{'url':'https://example.invalid/client.jar','sha1':'a'*40}},
                   'assetIndex':{'id':'assets-fixture'},'logging':{'client':{'fixture':'preserve'}},
                   'libraries':[{'name':'fixture:lib:1'},{'name':'fixture:lib:1:natives-windows'}]}

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.temp.cleanup()

    def installer(self,old=False,extra=None,profile_updates=None):
        if old:
            profile={'install':{'minecraft':'1.12.2','path':COORD,'filePath':'forge-universal.jar'},'versionInfo':self.patch}
            entries={'forge-universal.jar':self.forge}
        else:
            profile={'spec':0,'minecraft':'1.12.2','path':COORD,'json':'/version.json','processors':[]}
            entries={'maven/'+REL:self.forge,'version.json':json.dumps(self.patch).encode()}
        profile.update(profile_updates or {});entries['install_profile.json']=json.dumps(profile).encode();entries.update(extra or {})
        data=archive(entries);path=self.dir/'installer.jar';path.write_bytes(data)
        return path,hashlib.sha1(data).hexdigest()

    def run_probe(self,old=False,hash_override=None,mc='1.12.2',lv=VERSION,extra=None,profile_updates=None,download=False):
        path,digest=self.installer(old,extra,profile_updates);base=self.dir/'base.json';base.write_text(json.dumps(self.base))
        p=subprocess.run([str(JDK/'java.exe'),'-cp',str(CLASSES),'org.prosperomc.ForgeProbe',str(self.root),str(path),hash_override or digest,str(base),mc,lv]+(['download'] if download else []),capture_output=True,text=True,timeout=30)
        return p

    def test_no_processors_profile_preserves_client_and_replaces_conflicting_versions(self):
        p=self.run_probe(download=False);self.assertEqual(p.returncode,0,p.stderr)
        merged=json.loads((self.root/'merged.json').read_text());names=[i['name'] for i in merged['libraries']]
        self.assertNotIn('fixture:lib:1',names);self.assertIn('fixture:lib:2',names);self.assertIn('fixture:lib:1:natives-windows',names)
        self.assertEqual(merged['downloads'],self.base['downloads']);self.assertEqual(merged['assetIndex'],self.base['assetIndex'])
        self.assertEqual(merged['id'],'1.12.2');self.assertEqual(merged['mainClass'],'net.minecraft.launchwrapper.Launch')
        self.assertIn('FMLTweaker',merged['minecraftArguments']);self.assertEqual(merged['logging'],self.base['logging'])
        self.assertEqual((self.root/'libraries'/REL).read_bytes(),self.forge)
        spec=next(i for i in merged['libraries'] if i['name']==COORD)['downloads']['artifact']
        self.assertEqual(spec['sha1'],hashlib.sha1(self.forge).hexdigest())

    def test_legacy_version_info_and_checksums_normalize(self):
        self.base['libraries']=[]
        self.patch['libraries'][0]={'name':COORD,'url':self.url+'/'}
        rel='fixture/lib/2/lib-2.jar';self.blobs['/'+rel]=self.lib
        self.patch['libraries'][1]={'name':'fixture:lib:2','url':self.url+'/','checksums':[hashlib.sha1(self.lib).hexdigest()]}
        p=self.run_probe(old=True,download=True);self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual((self.root/'libraries'/rel).read_bytes(),self.lib)

    def test_corrupt_installer_hash_rejected(self):
        p=self.run_probe(hash_override='0'*40);self.assertNotEqual(p.returncode,0);self.assertIn('installer integrity mismatch',p.stderr)

    def test_embedded_artifact_digest_rejected(self):
        self.spec['sha1']='0'*40;p=self.run_probe();self.assertNotEqual(p.returncode,0);self.assertIn('Embedded Forge artifact integrity mismatch',p.stderr)
        self.assertFalse((self.root/'libraries'/REL).exists())

    def test_processor_installers_rejected_before_merge(self):
        p=self.run_probe(profile_updates={'processors':[{'jar':'dangerous:processor:1'}]})
        self.assertNotEqual(p.returncode,0);self.assertIn('processors are unsupported',p.stderr);self.assertFalse((self.root/'merged.json').exists())

    def test_traversal_archive_and_coordinate_paths_rejected(self):
        p=self.run_probe(extra={'../outside.jar':b'bad'});self.assertNotEqual(p.returncode,0);self.assertIn('Path escapes destination',p.stderr)
        self.spec['path']='../../outside.jar';p=self.run_probe();self.assertNotEqual(p.returncode,0);self.assertIn('coordinate/path mismatch',p.stderr)
        self.assertFalse((self.dir/'outside.jar').exists())

    def test_unsupported_minecraft_forge_and_mainclass_rejected(self):
        p=self.run_probe(mc='1.20.1');self.assertNotEqual(p.returncode,0);self.assertIn('1.12.2 only',p.stderr)
        p=self.run_probe(lv='47.1.0');self.assertNotEqual(p.returncode,0);self.assertIn('Unsupported legacy Forge version',p.stderr)
        self.patch['mainClass']='cpw.mods.modlauncher.Launcher';p=self.run_probe();self.assertNotEqual(p.returncode,0);self.assertIn('Unsupported Forge launch profile',p.stderr)

if __name__=='__main__': unittest.main()
