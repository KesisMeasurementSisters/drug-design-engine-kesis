"""Pin legacy array/line capacity regressions found during the source audit."""
import json,sys
from pathlib import Path
base,out=map(Path,sys.argv[1:]);out.mkdir(exist_ok=False)
s=(base/'minimal.cif').read_text();lines=s.splitlines();tags=[x for x in lines if x.startswith('_atom_site.')];rows=[x.split() for x in lines if x.startswith('ATOM ')]
cases=[]
for count in (31,32,33,63):
    name=f'columns-{count}';t=tags+[f'_atom_site.extra_{i}' for i in range(count-len(tags))]
    r=[row+['x']*(count-len(tags)) for row in rows]
    path=out/(name+'.cif');path.write_text('data_columns\nloop_\n'+'\n'.join(t)+'\n'+'\n'.join(' '.join(x) for x in r)+'\n#\n')
    cases.append({'name':name,'file':path.name,'reader':'pdbx','valid':count==31,'atoms':json.loads((base/'cases.json').read_text())[0]['atoms']})
# Unknown fields must not push an otherwise valid atom row past the legacy line buffer.
t=tags+[f'_atom_site.extra_{i}' for i in range(5)];r=[row+['X'*1000]*5 for row in rows]
p=out/'overlong-row.cif';p.write_text('data_columns\nloop_\n'+'\n'.join(t)+'\n'+'\n'.join(' '.join(x) for x in r)+'\n#\n')
cases.append({'name':'overlong-row','file':p.name,'reader':'pdbx','valid':False})
s=(out/'columns-63.cif').read_text().splitlines()
t=[x for x in s if x.startswith('_atom_site.')];r=[x.split() for x in s if x.startswith('ATOM ')]
order=list(range(22,63))+list(range(22));p=out/'interleaved-columns.cif'
p.write_text('data_interleaved\nloop_\n'+'\n'.join(t[i] for i in order)+'\n'+'\n'.join(' '.join(row[i] for i in order) for row in r)+'\n#\n')
cases.append({'name':'interleaved-columns','file':p.name,'reader':'pdbx','valid':False})
(out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
