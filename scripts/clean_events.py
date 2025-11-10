import os, shutil, re
from pathlib import Path
p = Path(__file__).resolve().parent.parent / 'logs' / 'events.csv'
bak = p.with_suffix('.csv.cleaned.bak')
shutil.copy2(p, bak)
print('Backup written to', bak)
new_lines = []
header = 'ts,role,requested_power,applied_power,temperature,override,client_ip,user_agent,request_path,request_method,client_id,event_type'
new_lines.append(header)
with p.open('r', encoding='utf-8') as f:
    lines = f.readlines()
# skip original header (first line) and process following
for i, line in enumerate(lines[1:], start=2):
    s = line.strip('\n\r')
    if not s:
        # skip blank lines
        continue
    # first field before comma
    first = s.split(',', 1)[0]
    if re.match(r'^\d+$', first):
        # keep line
        new_lines.append(s)
    else:
        # skip malformed line
        print(f'Skipping malformed line {i}: starts with "{first}"')
# write back
with p.open('w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines) + '\n')
print('Wrote cleaned events.csv with', len(new_lines)-1, 'rows')
