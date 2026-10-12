"""Audit publishable worktree files and all reachable Git blobs without printing secrets."""
import hashlib,json,re,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATTERNS={
    'private-key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github-token':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'aws-access-key':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'saved-oauth-token':re.compile(rb'(?i)["\'](?:accessToken|refreshToken|client_secret)["\']\s*:\s*["\'](?!fixture|test|example|mock|<)[A-Za-z0-9_./+=-]{40,}["\']'),
}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def scan(data,location,findings):
    for category,pattern in PATTERNS.items():
        if pattern.search(data):findings.append({'location':location,'category':category})

if __name__=='__main__':
    paths=git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0')
    findings=[];files=0
    for relative in paths:
        if not relative:continue
        path=ROOT/relative
        if not path.is_file():continue
        if path.is_symlink():raise ValueError('Symlink requires publication review: '+relative)
        scan(path.read_bytes(),relative,findings);files+=1
    objects={}
    for line in git('rev-list','--objects','--all').decode().splitlines():
        oid,_,name=line.partition(' ');objects[oid]=name
    process=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    blobs=0;blob_bytes=0
    try:
        for oid,name in objects.items():
            process.stdin.write((oid+'\n').encode());process.stdin.flush()
            header=process.stdout.readline().split();size=int(header[2]);data=process.stdout.read(size)
            if len(data)!=size or process.stdout.read(1)!=b'\n':raise ValueError('Incomplete Git object read')
            if header[1]==b'blob':scan(data,'history:'+oid[:12]+':'+name,findings);blobs+=1;blob_bytes+=size
    finally:process.stdin.close();process.stdout.close();process.wait()
    receipt={'worktreeFilesRead':files,'historyBlobsRead':blobs,'historyBytesRead':blob_bytes,
             'findings':findings,'limits':'Pattern scan is not proof that arbitrary secrets or personal data are absent. Never prints matching values.'}
    output=ROOT/'artifacts/publication-review';output.mkdir(parents=True,exist_ok=True)
    (output/'source-audit.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt));raise SystemExit(1 if findings else 0)
