"""Reproduce virtual-drive root lstat failure, then test the corrected CWD shim."""
from pathlib import Path
import hashlib
import re
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
upstream=root/'.deps/source/prospero-win-644e32e400c555e340d507383398c5d21b39b0b0'
cwd=upstream/'wine/ps5/pw_wine_cwd.c'
backup=root/'artifacts/wine-core-rootfix/pw_wine_cwd-original.c'
if backup.exists():cwd=backup
assert hashlib.sha256(cwd.read_bytes()).hexdigest()=='b7dfab538e459da54c90156b7171de28216a544270a2d9af72e6d7e4533ee730'
wrapper=upstream/'wine/ps5/pw_wine_cwd_libc.c'
flags=['-Wl,--wrap='+name.removeprefix('__wrap_') for name in sorted(set(re.findall(r'__wrap_[a-z_]+',wrapper.read_text())))]
test=(upstream/'tests/test_pw_wine_cwd.c').read_text()
anchor='    assert(!lstat("dosdevices/c:", &st) && S_ISLNK(st.st_mode));'
assert test.count(anchor)==1
test=test.replace(anchor,anchor+'''
    assert(!lstat("dosdevices/c:/", &st) && S_ISDIR(st.st_mode));
    assert(!lstat("dosdevices/c:////", &st) && S_ISDIR(st.st_mode));
    assert(!fstatat(AT_FDCWD,"dosdevices/c:/", &st, AT_SYMLINK_NOFOLLOW) && S_ISDIR(st.st_mode));
    assert(!lstat("dosdevices/z:/", &st) && S_ISDIR(st.st_mode));
    assert(readlink("dosdevices/c:/", buffer, sizeof(buffer))==-1 && errno==EINVAL);
''')
anchor='    assert(!fstatat(dir_fd, "link", &st, AT_SYMLINK_NOFOLLOW) && S_ISLNK(st.st_mode));'
assert test.count(anchor)==1
test=test.replace(anchor,anchor+'''
    assert(lstat("link/", &st)==-1 && errno==ENOTDIR);
    assert(fstatat(dir_fd,"link/", &st, AT_SYMLINK_NOFOLLOW)==-1 && errno==ENOTDIR);
''')
with tempfile.TemporaryDirectory(prefix='prosperomc-drive-links-') as folder:
    folder=Path(folder);file=folder/'check.c';file.write_text(test)
    for label,unit in [('baseline',cwd),('fixed',root/'vendor/prospero-win/wine/ps5/pw_wine_cwd.c')]:
        binary=folder/label
        subprocess.run(['clang-18','-O2','-std=gnu11','-Wall','-Wextra','-Werror','-pthread',
                        '-U_FORTIFY_SOURCE','-D_FORTIFY_SOURCE=0','-fsanitize=address,undefined',
                        '-I'+str(upstream/'include'),'-I'+str(upstream/'wine/ps5'),str(file),str(unit),str(wrapper),*flags,'-o',str(binary)],check=True)
        result=subprocess.run([str(binary)],capture_output=True,text=True)
        if label=='baseline':
            assert result.returncode and 'lstat("dosdevices/c:/"' in result.stderr,result
            print('BASELINE_REPRODUCED: existing virtual C: root fails lstat with trailing slash')
        else:
            assert result.returncode==0,result.stderr
            print(result.stdout.strip())
            print('DRIVE_ROOT_LINK_FIX_PASS: directory roots, repeated slashes, no-follow fstatat, ordinary link identity and file-link ENOTDIR preserved')
