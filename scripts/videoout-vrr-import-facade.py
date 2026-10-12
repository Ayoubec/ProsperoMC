"""Extend link-only public SDK VideoOut imports; no facade executes on PS5."""
import re, subprocess, sys
from pathlib import Path
sdk, output = map(Path, sys.argv[1:])
listing=subprocess.check_output(['llvm-readelf-18','--dyn-syms','--wide',str(sdk)],text=True)
symbols=set()
for line in listing.splitlines():
    fields=line.split()
    if len(fields)==8 and fields[6]!='UND' and fields[4]=='GLOBAL' and re.fullmatch(r'sceVideoOut[A-Za-z0-9_]+',fields[7]):
        symbols.add(fields[7])
if len(symbols)<100:raise ValueError('Unexpected VideoOut SDK facade')
symbols.update(('sceVideoOutVrrUnpegFromFixedRate','sceVideoOutVrrPegToFixedRate'))
output.write_text('/* Link-only facade: firmware implements these symbols. */\n'+''.join('void '+name+'(void) {}\n' for name in sorted(symbols)))
print('VIDEOOUT_IMPORT_FACADE',len(symbols))
