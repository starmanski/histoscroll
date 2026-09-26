from pathlib import Path
import sys

root = Path(sys.argv[1])
p = root / 'pc-generator' / 'HistoScroll_PC_Generator.py'
s = p.read_text(encoding='utf-8')
s = s.replace(".pack(side='left',pad=(0,18))", ".pack(side='left',padx=(0,18))")
s = s.replace(".pack(side='left',pad=(8,0))", ".pack(side='left',padx=(8,0))")
if "pad=" in s:
    raise SystemExit('unexpected Tkinter pack pad= option remains')
p.write_text(s, encoding='utf-8')
print('Tkinter generator hotfix applied')
