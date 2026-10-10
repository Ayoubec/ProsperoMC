"""Exercise public download APIs with the packaged Java 8 backend on the host.

All output stays under artifacts/live-downloads. This does not deploy or launch
games. --install-pack also installs the newest listed Fabulously Optimized pack
into this isolated test directory; it does not certify PS5 compatibility.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

repo=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--install-pack',action='store_true')
args=parser.parse_args()
root=repo/'artifacts/live-downloads/data'
root.mkdir(parents=True,exist_ok=True)
java=repo/'dist/PPSA99888/prosperomc/runtimes/java8/bin/java.exe'
jar=repo/'artifacts/launcher/prosperomc-launcher.jar'
request=root.parent/'request.properties'

def props(p):
    return dict(line.split('=',1) for line in p.read_text(encoding='utf-8').splitlines() if line and not line.startswith('#'))

def command(**values):
    request.write_text(''.join(f'{k}={v}\n' for k,v in values.items()),encoding='utf-8')
    result=subprocess.run([str(java),'-jar',str(jar),'--root',str(root),'--request',str(request)],
        capture_output=True,text=True,timeout=1800)
    (root.parent/(values['command']+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
    print(values['command'],result.returncode,result.stdout.strip(),flush=True)
    if result.returncode:raise RuntimeError(result.stderr)
    return props(root/'launcher-view.properties')

command(command='catalog')
view=command(command='pack-search',query='Fabulously Optimized')
project=next(view[f'remote.pack.{i}.id'] for i in range(int(view['remote.pack.count']))
             if view[f'remote.pack.{i}.name'].lower()=='fabulously optimized')
view=command(command='pack-versions',projectId=project)
release=view['remote.version.0.id']
metadata=json.loads((root/'cache/modrinth-versions.json').read_text(encoding='utf-8'))
version=next(v for v in metadata if v['id']==release)
file=next(f for f in version['files'] if f['filename'].endswith('.mrpack') and f.get('primary'))
archive=root/'imports'/f'{project}-{release}.mrpack'
archive.parent.mkdir(exist_ok=True)
req=urllib.request.Request(file['url'],headers={'User-Agent':'Ayoubec/ProsperoMC download verification'})
with urllib.request.urlopen(req,timeout=60) as response:
    archive.write_bytes(response.read(32*1024*1024))
data=archive.read_bytes()
assert len(data)==file['size']
assert hashlib.sha1(data).hexdigest()==file['hashes']['sha1']
assert hashlib.sha512(data).hexdigest()==file['hashes']['sha512']
command(command='install-java',major=17)
receipt={'hostJava':'packaged Java 8','project':project,'release':release,'name':version['name'],
         'minecraft':version['game_versions'],'modrinthArchiveVerified':True,'java17DownloadedVerified':True,
         'consoleVerified':False}
if args.install_pack:
    command(command='pack-download',projectId=project,packVersion=release)
    receipt['packInstalledOnHost']=True
(root.parent/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt),flush=True)
