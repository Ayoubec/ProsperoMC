"""Compile the draw driver and native backend from verified CI sources."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
from graphics_vertex_formats import patch_compiler

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
shutil.copy2(out / 'ps5_agc_native_runtime.c',source / 'src/platform/ps5_agc_native_runtime.c')
# The earlier driver-only builds did not need the compiler's external headers.
# Reuse the exact archives shipped with the verified SDK for the changed unit.
for dependency, header in (
    ('opengnm', 'include/gnm_shaderbinary.h'),
    ('Vulkan-Headers', 'include/vulkan/vulkan.h'),
    ('SPIRV-Headers', 'include/spirv/spir-v.xml'),
):
    destination = source / 'third_party' / dependency
    if (destination / header).is_file():
        continue
    package = next((root / '.deps/graphics-sdk-ci-738f94c').glob('ps5-opengl-sdk-*.tar.gz'))
    with tarfile.open(package) as archive:
        member = next(m for m in archive if m.name.endswith('/sources/' + dependency + '.tar'))
        saved = work / (dependency + '.tar')
        saved.write_bytes(archive.extractfile(member).read())
    extracted = work / ('compiler-headers-' + dependency)
    extract(saved, extracted, provenance['source_archives'][dependency + '.tar'])
    located = next(extracted.rglob(Path(header).name))
    dep_root = located
    for _ in Path(header).parts:
        dep_root = dep_root.parent
    shutil.copytree(dep_root, destination, dirs_exist_ok=True)
compiler_diff = patch_compiler(psbc, out / 'integer-vertex-compiler.patch')
# Upstream's host bootstrap generates headers omitted from its standalone
# Makefile. Use that exact verified generation section without rebuilding the
# host compiler or inventing substitute Vulkan headers.
host_bootstrap = (source / 'toolchain/build-opengnm-psbc.sh').read_text()
generated_section = host_bootstrap.split('# These generated files', 1)[1].split('# Upstream enumerates', 1)[0]
run(['bash'], input='# These generated files' + generated_section,
    text=True, cwd=psbc)
run([sys.executable, root / 'scripts/fix-mesa-upload-lifetime.py',
     mesa / 'src/gallium/auxiliary/util/u_vbuf.c'])
run([sys.executable, root / 'scripts/check-mesa-upload-lifetime.py'])

targets = subprocess.check_output(['ninja','-C',str(build),'-t','targets','all'],text=True)
headers = [line.partition(': ')[0] for line in targets.splitlines() if line.partition(': ')[0].endswith('.h')]
run(['ninja','-C',build,'-j8',*headers])
vbuf_object = build / 'src/gallium/auxiliary/libgallium.a.p/util_u_vbuf.c.o'
run(['ninja', '-C', build, str(vbuf_object.relative_to(build))])
compiler_headers = ['src/amd/common/amdgfxregs.h','src/amd/common/sid_tables.h','src/compiler/nir/nir_builder_opcodes.h',
    'src/compiler/nir/nir_opcodes.h','src/compiler/nir/nir_intrinsics.h',
    'src/compiler/nir/nir_intrinsics_indices.h']
run(['make','-C',psbc,'-f',source / 'toolchain/Makefile.opengnm-psbc-ps5','-j8',*compiler_headers],
    env=dict(os.environ,PS5_PAYLOAD_SDK=str(payload)))
run(['make','-C',psbc,'-f',source / 'toolchain/Makefile.opengnm-psbc-ps5',
     '-j8', 'generated'], env=dict(os.environ,PS5_PAYLOAD_SDK=str(payload)))
compiler_env = dict(os.environ, PS5_PAYLOAD_SDK=str(payload))
compiler_recipe = subprocess.check_output([
    'make', '--dry-run', '--always-make', '--no-print-directory', '-C', str(psbc),
    '-f', str(source / 'toolchain/Makefile.opengnm-psbc-ps5'),
    'GENERATED=', 'libpsbc/psbc_compile.ps5.o'], text=True, env=compiler_env)
compiler_lines = [line for line in compiler_recipe.splitlines()
                  if line.startswith(str(payload / 'bin/prospero-clang') + ' ')]
if len(compiler_lines) != 1:
    raise ValueError('Compiler recipe must compile exactly one verified source unit')
compiler_command = shlex.split(compiler_lines[0])
if compiler_command[-4:] != ['-c', 'libpsbc/psbc_compile.c', '-o', 'libpsbc/psbc_compile.ps5.o']:
    raise ValueError('Compiler recipe output changed')
run(compiler_command, cwd=psbc, env=compiler_env)
run([sys.executable,root / 'scripts/check-shader-layout-cache.py'])
run([sys.executable,root / 'scripts/check-worker-shader-cache.py'])
run([sys.executable,root / 'scripts/check-batch-timings.py'])
run([sys.executable,root / 'scripts/check-descriptor-retirement.py'])
run([sys.executable,root / 'scripts/check-descriptor-ready-reuse.py'])
run([sys.executable,root / 'scripts/check-upstream-async.py'])
run([sys.executable,root / 'scripts/check-integer-vertex-formats.py'])
run(['gcc','-O2',out / 'check-policy.c','-o',work / 'check-policy'])
with (out / 'policy-check.log').open('w') as log:
    run([work / 'check-policy'],stdout=log)
# Reproduce CI flags. Production draws must not run per-operation clocks,
# serializing cycle reads, cache atomics or diagnostic I/O. Keep all submission,
# retirement and rendering features; profiling remains an explicit build option.
flags = shlex.split('\n'.join(config.splitlines()[1:]))
# Retain the currently tested 1 GiB pool while fixing the measured uploader
# lifetime leak. Increasing this pool alone did not prevent the modern crash.
arena_flag = '-DPS5_RENDER_ARENA_BYTES=0x10000000u'
assert flags.count(arena_flag) == 1
flags[flags.index(arena_flag)] = '-DPS5_RENDER_ARENA_BYTES=0x40000000u'
prefix = '/home/runner/work/ps5-opengl/ps5-opengl'
flags = [f.replace(prefix+'/build/mesa-ps5-probe',str(build)).replace(prefix,str(source)) for f in flags]
profile = os.environ.get('PROSPEROMC_DRAW_PROFILE', '0') == '1'
async_prepare = os.environ.get('PROSPEROMC_ASYNC_NATIVE_PREP', '1') == '1' and not profile
batch_timings = os.environ.get('PROSPEROMC_BATCH_TIMINGS', '0') == '1'
if not profile:
    flags = [f for f in flags if not f.startswith('-DPS5_DRAW_PROFILE')]
if async_prepare:
    flags += ['-DPS5_ASYNC_NATIVE_PREP=1','-DPS5_NATIVE_PREP_WORKERS=2']
if batch_timings:
    flags += ['-DPROSPEROMC_BATCH_TIMINGS=1']
(out / 'runtime-config.txt').write_text(shlex.join(flags)+'\n')
cache_id = hashlib.sha256((out / 'ps5_screen.c').read_bytes()+
    (psbc / 'libpsbc/psbc_compile.ps5.o').read_bytes()).hexdigest()
(work / 'shader-cache-build-id.h').write_text('#define PS5_SHADER_CACHE_BUILD_ID "'+cache_id+'"\n')
run([payload / 'bin/prospero-clang',*flags,'-I'+str(build / 'src/compiler'),'-include',work / 'shader-cache-build-id.h',
     '-I'+str(source / 'src/platform'),'-c',source / 'src/gallium/ps5/ps5_screen.c','-o',work / 'ps5_screen.o'])
# The backend includes the patched native runtime. Match its profiling
# configuration to the draw driver and retain the original entry-point rename.
run([payload / 'bin/prospero-clang',*flags,'-I'+str(build / 'src/compiler'),
     '-I'+str(source / 'src/platform'),'-Wno-error=unused-function',
     '-Dmain='+('ps5_agc_gate2_run_sync' if async_prepare else 'ps5_agc_gate2_run'),
     '-DAGC_TRIANGLE_SUBMIT=1','-DAGC_RUNTIME_PACKAGES=1',
     '-c',source / 'src/platform/ps5_agc_runtime_backend.c',
     '-o',work / 'ps5_agc_runtime_backend.o'])
modified.mkdir(parents=True, exist_ok=True)
shutil.copy2(out / 'runtime-config.txt',modified / 'runtime-config.txt')
shutil.copytree(ci / 'sdk',modified / 'sdk',dirs_exist_ok=True)
run(['llvm-ar-18', 'r', modified / 'sdk/lib/libgallium.a', vbuf_object])
compiler_archive = modified / 'sdk/lib/libpsbc.ps5.a'
compiler_members = subprocess.check_output(['llvm-ar-18', 't', compiler_archive],text=True).splitlines()
if compiler_members.count('psbc_compile.ps5.o') != 1:
    raise ValueError('Verified compiler archive has an unexpected compilation member')
run(['llvm-ar-18', 'r', compiler_archive, psbc / 'libpsbc/psbc_compile.ps5.o'])
shutil.copy2(psbc / 'libpsbc/psbc_compile.h', modified / 'sdk/include/psbc_compile.h')
runtime = modified / 'sdk/lib/libps5_opengl_core33.a'
run(['llvm-ar-18','r',runtime,work / 'ps5_screen.o',work / 'ps5_agc_runtime_backend.o'])
shutil.copy2(work / 'ps5_screen.o',out / 'ps5_screen.o')
shutil.copy2(work / 'ps5_agc_runtime_backend.o',out / 'ps5_agc_runtime_backend.o')
manifest = modified / 'sdk/manifest.sha256'
lines = []
for path in sorted((modified / 'sdk').rglob('*')):
    if path.is_file() and path != manifest:
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.relative_to(modified / 'sdk').as_posix())
manifest.write_text('\n'.join(lines)+'\n')
combined_patch = out / 'smooth-legacy-batching.patch'
patch_data = combined_patch.read_text()
compiler_marker = '--- a/third_party/opengnm-psbc/libpsbc/'
patch_data = patch_data.split(compiler_marker,1)[0] + compiler_diff.read_text()
combined_patch.write_text(patch_data)
patch_hash = hashlib.sha256(combined_patch.read_bytes()).hexdigest()
provenance.update(version=provenance['version']+'-prosperomc-quad-batching',
    original_sdk_manifest_sha256=provenance['sdk_manifest_sha256'],
    original_psbc_archive_sha256=provenance['psbc_archive_sha256'],
    psbc_archive_sha256=hashlib.sha256(compiler_archive.read_bytes()).hexdigest(),
    sdk_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    runtime_archive_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
    local_patch={'file':'smooth-legacy-batching.patch','sha256':patch_hash,
                 'description':'Fetch packed signed and unsigned integer vertices directly on GPU through matching driver/compiler formats, avoiding per-draw CPU conversion; release every retired Mesa vertex upload after driver binding on each draw; retain legacy batching and owned-buffer fixes; reclaim ready FIFO descriptors only between batches without waiting before empty-cache allocation, recycle retired descriptors, reuse byte-verified shader layouts, ' + ('enable upstream two-worker native command preparation and worker-local byte-verified shader hits, ' if async_prepare else '') + 'log only batch errors, and ' + ('enable diagnostic profiling' if profile else 'disable hot-path profiling') + ' in the draw driver and native backend'},
    draw_profile=profile,
    batch_timings=batch_timings,
    async_native_prepare=async_prepare,
    native_prepare_workers=2 if async_prepare else 0,
    gpu_buffer_pool_bytes=1073741824,
    native_integer_vertex_formats=True,
    compiler_archive_sha256=hashlib.sha256(compiler_archive.read_bytes()).hexdigest(),
    runtime_config_sha256=hashlib.sha256((out / 'runtime-config.txt').read_bytes()).hexdigest(),
    hardware_validation='pending console retest of modified draw driver')
(modified / 'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('MODIFIED_RUNTIME_ARCHIVE',provenance['runtime_archive_sha256'],flush=True)
