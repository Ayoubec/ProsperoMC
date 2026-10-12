"""Build and verify sanitized first-install/update archives from a validated local stage."""
import argparse,hashlib,importlib.util,json,re,shutil,subprocess,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TITLE=ROOT/'dist/PPSA99888'
DATA=TITLE/'prosperomc'
TOP={'APP-SOURCES.txt','eboot.bin','lapy-manifest.json','lapy.elf','LICENSE',
     'MESA_ZINK_REPORT.json','PROSPERO-WIN-LICENSE','PROSPERO-WIN-LICENSING.md',
     'PROSPERO-WIN-NOTICE.md','PROSPERO-WIN-PROSPEROMC-ADAPTATIONS.md','STAGE-REPORT.json',
     'THIRD_PARTY_NOTICES.md','WEBP_LICENSE.txt','WEBP_PATENTS.txt','WINE_CORE_V020_LICENSE.txt',
     'WINE_CORE_V020_REPORT.json','WINE_CORE_V020_SOURCES.txt','WINE_LICENSE','WINE_SOURCES.txt',
     'WINE_THIRD_PARTY.md','ZINK_SOURCES.txt'}
DIRS={'launcher','LICENSES','sce_module','sce_sys','win','WINE_PATCHES','ZINK_LICENSES'}
DENIED={'private','instances','versions','libraries','assets','imports','cache','profiles',
        'logs','diagnostics','accounts.json','account.json','settings.properties','auth-pending.json',
        'launch-plan.json','launch.profile','launcher-view.properties','request.properties','response.properties',
        'prosperomc-profile-next'}

def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()

def copied(source,destination):
    if source.is_symlink():raise ValueError('Release source contains a symlink')
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)

def redact(value):
    if isinstance(value,dict):return {key:redact(item) for key,item in value.items()}
    if isinstance(value,list):return [redact(item) for item in value]
    if isinstance(value,str) and ('C:\\Users\\' in value or '/mnt/c/Users/' in value or '/home/' in value):return '(local build path)'
    return value

def online_document(source,revision):
    base=f'https://github.com/Ayoubec/ProsperoMC/blob/{revision}/'
    text=source.read_text(encoding='utf-8-sig')
    # Package documentation links to the corresponding published source tree.
    parent=source.relative_to(ROOT).parent.as_posix()
    def link(target,image=False):
        if target.startswith(('https://','http://','#')):return target
        import posixpath
        normalized=posixpath.normpath(posixpath.join(parent,target))
        return (f'https://raw.githubusercontent.com/Ayoubec/ProsperoMC/{revision}/' if image else base)+normalized
    text=re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',lambda m:m[1]+'('+link(m[2],m[1].startswith('!'))+')',text)
    text=re.sub(r'(src|href)="([^"]+)"',lambda m:m[1]+'="'+link(m[2],m[1]=='src')+'"',text)
    return text

def inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(root).as_posix()
        if path.is_symlink() or any(part.lower() in DENIED for part in Path(relative).parts):
            raise ValueError('Private/game/mutable data in release: '+relative)
        if path.suffix in {'.jfr','.log','.hprof','.ppm'}:raise ValueError('Test capture in release')
        if '/drive_c/users/' in relative:raise ValueError('Wine user directory in release')
        result[relative]={'bytes':path.stat().st_size,'sha256':digest(path)}
    return result

def archive(root,destination):
    files=inventory(root)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zipped:
        for name in files:zipped.write(root/name,name)
        zipped.writestr('RELEASE-MANIFEST.json',json.dumps(files,indent=2))
    verify(destination)
    return {'archive':destination.name,'bytes':destination.stat().st_size,'sha256':digest(destination),'files':len(files)}

def verify(path):
    with zipfile.ZipFile(path) as zipped:
        manifest=json.loads(zipped.read('RELEASE-MANIFEST.json'))
        if set(zipped.namelist())!=set(manifest)|{'RELEASE-MANIFEST.json'}:raise ValueError('Release manifest file set differs')
        for name,item in manifest.items():
            if name.startswith('/') or '..' in Path(name).parts:raise ValueError('Unsafe release archive path')
            if any(part.lower() in DENIED for part in Path(name).parts):raise ValueError('Forbidden release archive path')
            h=hashlib.sha256();count=0
            with zipped.open(name) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block);count+=len(block)
            if h.hexdigest()!=item['sha256'] or count!=item['bytes']:raise ValueError('Release archive readback differs: '+name)
    print('RELEASE_ARCHIVE_VERIFIED',path.name,len(manifest),flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--version',default='v0.1.0-early');parser.add_argument('--verify',type=Path);args=parser.parse_args()
    if args.verify:verify(args.verify);return
    if not args.version.replace('.','').replace('-','').isalnum():raise ValueError('Invalid version')
    output=ROOT/'artifacts/releases'/args.version;output.mkdir(parents=True,exist_ok=True)
    full=output/'install';update=output/'update'
    if full.exists() or update.exists():raise ValueError('Release staging exists; inspect it instead of silently replacing')
    spec=importlib.util.spec_from_file_location('deploy',ROOT/'scripts/deploy-ps5.py');deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)
    deploy.validate_package(TITLE,DATA)
    for source in TITLE.rglob('*'):
        if not source.is_file():continue
        relative=source.relative_to(TITLE)
        if relative.parts[0] in DIRS or relative.as_posix() in TOP:
            copied(source,full/'PPSA99888'/relative);copied(source,update/'PPSA99888'/relative)
    for folder in ('launcher','runtimes/java8','prefixes/minecraft'):
        for source in (DATA/folder).rglob('*'):
            if not source.is_file():continue
            relative=source.relative_to(DATA)
            if folder=='prefixes/minecraft':
                below=source.relative_to(DATA/folder)
                if below.parts[0]=='drive_c' and (len(below.parts)<2 or below.parts[1]!='windows'):continue
                if below.parts[0] not in {'drive_c','dosdevices','system.reg','user.reg','userdef.reg','prosperomc-prefix.json','.update-timestamp'}:continue
            copied(source,full/'prosperomc'/relative)
    for relative in ('launcher/prosperomc-launcher.jar','launcher/prosperomc-zipfs.jar',
                     'prefixes/minecraft/drive_c/windows/system32/ntdll.dll',
                     'prefixes/minecraft/drive_c/windows/syswow64/ntdll.dll'):
        copied(DATA/relative,update/'prosperomc'/relative)
    source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for stage in (full,update):
        for relative in ('PPSA99888/STAGE-REPORT.json','prosperomc/STAGE-REPORT.json'):
            report=redact(json.loads((TITLE/'STAGE-REPORT.json').read_text()))
            report['publicRelease']={'version':args.version,'sourceRevision':source_revision,'gameFilesIncluded':False,
                                     'privateStateIncluded':False,'freshConsoleInstallVerified':False}
            target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2))
        for name in ('LICENSE','LICENSES.md','THIRD_PARTY_NOTICES.md'):copied(ROOT/name,stage/name)
        (stage/'README.md').write_text(online_document(ROOT/'README.md',source_revision))
        (stage/'RELEASE-NOTES.md').write_text(online_document(ROOT/'docs/releases/alpha.md',source_revision))
        (stage/'SOURCE-LINKS.md').write_text(
            '# Corresponding sources\n\n'
            f'ProsperoMC and local build/patch recipes: https://github.com/Ayoubec/ProsperoMC/tree/{source_revision}\n\n'
            'Wine/Mesa/driver sources and exact revisions: PPSA99888/WINE_SOURCES.txt, WINE_CORE_V020_SOURCES.txt and ZINK_SOURCES.txt. Local changes accompany these in PPSA99888/WINE_PATCHES. Component licenses are included.\n\n'
            'Temurin 8u504-b01: https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk-sources_8u504b01.tar.gz\n\n'
            'The initial offline Wine prefix is made with Ubuntu Wine10.0~repack-12ubuntu1. Corresponding distro sources: https://launchpad.net/ubuntu/+source/wine/10.0~repack-12ubuntu1\n')
    deploy.validate_package(full/'PPSA99888',full/'prosperomc')
    receipts=[archive(full,output/f'ProsperoMC-{args.version}.zip'),archive(update,output/f'ProsperoMC-{args.version}-update.zip')]
    (output/'SHA256SUMS.txt').write_text(''.join(item['sha256']+'  '+item['archive']+'\n' for item in receipts))
    (output/'package-receipt.json').write_text(json.dumps(receipts,indent=2))
    print('PUBLIC_RELEASE_PACKAGES_READY',json.dumps(receipts))

if __name__=='__main__':main()
