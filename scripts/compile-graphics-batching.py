"""Compile one modified runtime object using the official CI's source/flags."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile

root = Path(__file__).resolve().parent.parent
work = Path(sys.argv[1]).resolve()
assert str(work) == '/tmp/prosperomc-graphics-performance'
ci = root / '.deps/graphics-sdk-ci-738f94c/extracted'
out = root / 'artifacts/graphics-batching'
modified = root / '.deps/graphics-sdk-batching'
source = work / 'source'
mesa = source / 'third_party/mesa-26.2.0'
psbc = source / 'third_party/opengnm-psbc'
build = work / 'mesa-build'
provenance = json.loads((ci / 'provenance.json').read_text())

def run(args, **kwargs):
    print('RUN', shlex.join(map(str,args)), flush=True)
    return subprocess.run(list(map(str,args)), check=True, **kwargs)

def extract(archive, target, expected):
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        # Official source snapshots may have a single archive root.
        members = tar.getmembers()
        for m in members:
            assert not m.name.startswith('/') and '..' not in Path(m.name).parts
        tar.extractall(target, filter='data')

payload = work / 'sdk'
config = (ci / 'runtime-config.txt').read_text()
source_ready = (build / 'build.ninja').is_file() and (payload / 'bin/prospero-clang').is_file() and (source / 'src/gallium/ps5/ps5_screen.c').is_file() and (psbc / 'libpsbc/psbc_compile.h').is_file() and 'flat_input_vertex_valid' in (psbc / 'libpsbc/psbc_compile.h').read_text()
if source_ready:
    shutil.copy2(out / 'ps5_screen.c', source / 'src/gallium/ps5/ps5_screen.c')
if not source_ready:
    extract(ci / 'sources/ps5-opengl.tar', work / 'gl-source', provenance['source_archives']['ps5-opengl.tar'])
    original_source = next((work / 'gl-source').rglob('src/gallium/ps5/ps5_screen.c')).parents[3]
    source.mkdir(exist_ok=True)
    shutil.copytree(original_source, source, dirs_exist_ok=True)
    extract(root / '.deps/archives/mesa-26.2.0.tar.xz', source / 'third_party',
            'efd4bb08cdb7c365a812cd4e6c9202ab55b2f22cdcd13c7d6c4f9647b799a4ef')
    # The CI source package includes the exact compiler header snapshot.
    archive = next((root / '.deps/graphics-sdk-ci-738f94c').glob('ps5-opengl-sdk-*.tar.gz'))
    with tarfile.open(archive) as tar:
        entry = next(m for m in tar.getmembers() if m.name.endswith('/sources/opengnm-psbc.tar'))
        compiler_tar = work / 'psbc.tar'
        compiler_tar.write_bytes(tar.extractfile(entry).read())
        config = tar.extractfile(next(m for m in tar.getmembers() if m.name.endswith('/runtime-config.txt'))).read().decode()
    extract(compiler_tar, work / 'compiler-source', provenance['source_archives']['opengnm-psbc.tar'])
    compiler_source = next((work / 'compiler-source').rglob('libpsbc/psbc_compile.h')).parents[1]
    shutil.copytree(compiler_source, psbc, dirs_exist_ok=True)
    compiler_patch = (source / 'toolchain/opengnm-psbc-ps5.patch').read_text()
    # A saved build can retain files created by this platform patch. Recreate only
    # those exact generated additions; tracked files came from the verified archive.
    for part in compiler_patch.split('diff --git ')[1:]:
        if '\n--- /dev/null\n' not in part:
            continue
        name = next(line[6:] for line in part.splitlines() if line.startswith('+++ b/'))
        target = (psbc / name).resolve()
        assert target.is_relative_to(psbc.resolve())
        target.unlink(missing_ok=True)
    run(['patch','--batch','--forward','-p1','-d',psbc],
        input=compiler_patch,text=True)
    run(['bash',source / 'toolchain/apply-mesa-ps5-patch.sh',mesa,
         root / '.deps/archives/mesa-26.2.0.tar.xz',source / 'toolchain/mesa-ps5.patch'])
    shutil.copy2(out / 'ps5_screen.c', source / 'src/gallium/ps5/ps5_screen.c')
    foundation = root / '.deps/source/ps5-native-app-boilerplate-9c0b994a048521af6fb84c73ded364504fe250e9'
    payload = work / 'sdk'
    shutil.copytree(foundation / '.deps/native/ps5-payload-sdk', payload, dirs_exist_ok=True)
    cross = work / 'prospero.ini'
    text = (payload / 'toolchain/prospero.ini').read_text().replace('@DIRNAME@',str(payload / 'toolchain')).replace('[target_machine]','[host_machine]')
    cross.write_text(text)
    reconfigure = ['--reconfigure'] if (build / 'build.ninja').exists() else []
    run(['meson','setup',*reconfigure,build,mesa,'--cross-file='+str(cross),'--buildtype=release','-Db_ndebug=true',
         '-Dplatforms=','-Dgallium-drivers=softpipe','-Dvulkan-drivers=','-Dopengl=true',
         '-Degl=disabled','-Dgbm=disabled','-Dgles1=disabled','-Dgles2=disabled','-Dglx=disabled',
         '-Dllvm=disabled','-Dzlib=disabled','-Dzstd=disabled','-Dshader-cache=disabled',
         '-Dxmlconfig=disabled','-Dexpat=disabled','-Dlibunwind=disabled','-Dvalgrind=disabled',
         '-Dvideo-codecs=','-Dbuild-tests=false','-Dtools=','-Dgallium-va=disabled','-Dgallium-rusticl=false'])
if source_ready:
    cross = work / 'prospero.ini'
    if not cross.exists():
        cross.write_text((payload / 'toolchain/prospero.ini').read_text().replace('@DIRNAME@',str(payload / 'toolchain')).replace('[target_machine]','[host_machine]'))

targets = subprocess.check_output(['ninja','-C',str(build),'-t','targets','all'],text=True)
headers = [line.partition(': ')[0] for line in targets.splitlines() if line.partition(': ')[0].endswith('.h')]
run(['ninja','-C',build,'-j8',*headers])
compiler_headers = ['src/amd/common/amdgfxregs.h','src/amd/common/sid_tables.h','src/compiler/nir/nir_builder_opcodes.h',
    'src/compiler/nir/nir_opcodes.h','src/compiler/nir/nir_intrinsics.h',
    'src/compiler/nir/nir_intrinsics_indices.h']
run(['make','-C',psbc,'-f',source / 'toolchain/Makefile.opengnm-psbc-ps5','-j8',*compiler_headers],
    env=dict(os.environ,PS5_PAYLOAD_SDK=str(payload)))
run(['gcc','-O2',out / 'check-policy.c','-o',work / 'check-policy'])
with (out / 'policy-check.log').open('w') as log:
    run([work / 'check-policy'],stdout=log)
# Reproduce CI flags, changing paths only. Leave profiling enabled to compare
# draw counts against the previous build; optimization changes no synchronization.
flags = shlex.split('\n'.join(config.splitlines()[1:]))
prefix = '/home/runner/work/ps5-opengl/ps5-opengl'
flags = [f.replace(prefix+'/build/mesa-ps5-probe',str(build)).replace(prefix,str(source)) for f in flags]
cache_id = hashlib.sha256((out / 'ps5_screen.c').read_bytes()+(ci / 'sdk/lib/libpsbc.ps5.a').read_bytes()).hexdigest()
(work / 'shader-cache-build-id.h').write_text('#define PS5_SHADER_CACHE_BUILD_ID "'+cache_id+'"\n')
run([payload / 'bin/prospero-clang',*flags,'-I'+str(build / 'src/compiler'),'-include',work / 'shader-cache-build-id.h',
     '-I'+str(source / 'src/platform'),'-c',source / 'src/gallium/ps5/ps5_screen.c','-o',work / 'ps5_screen.o'])
modified.mkdir(parents=True, exist_ok=True)
shutil.copytree(ci / 'sdk',modified / 'sdk',dirs_exist_ok=True)
runtime = modified / 'sdk/lib/libps5_opengl_core33.a'
run(['llvm-ar-18','r',runtime,work / 'ps5_screen.o'])
shutil.copy2(work / 'ps5_screen.o',out / 'ps5_screen.o')
manifest = modified / 'sdk/manifest.sha256'
lines = []
for path in sorted((modified / 'sdk').rglob('*')):
    if path.is_file() and path != manifest:
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.relative_to(modified / 'sdk').as_posix())
manifest.write_text('\n'.join(lines)+'\n')
patch_hash = hashlib.sha256((out / 'smooth-legacy-batching.patch').read_bytes()).hexdigest()
provenance.update(version=provenance['version']+'-prosperomc-quad-batching',
    original_sdk_manifest_sha256=provenance['sdk_manifest_sha256'],
    sdk_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    runtime_archive_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
    local_patch={'file':'smooth-legacy-batching.patch','sha256':patch_hash,
                 'description':'Keep eligible multi-draw groups in the existing deferred queue; batch legacy quads and non-indexed triangles/strips; reuse immutable indices and static publication; retain indexed/GPU-write/export guards'},
    hardware_validation='pending console retest of modified draw driver')
(modified / 'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('MODIFIED_RUNTIME_ARCHIVE',provenance['runtime_archive_sha256'],flush=True)
