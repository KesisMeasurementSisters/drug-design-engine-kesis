"""Regression contracts for the local fpocket repair; independent synthetic cases."""
import json
import math
import sys
from pathlib import Path
import pytest
from dde.core.errors import ArtifactError
from dde.core.pocket_runtime import validate_input, run_bounded, validate_pockets, publication

PDB=f"ATOM  {1:5d}  CA  ALA A{145:4d}A   {12.:8.3f}{13.:8.3f}{14.:8.3f}  1.00 20.00           C  \n"

@pytest.mark.parametrize('token',['     nan','     inf',' INVALID','        ','  1_0.00','   １２.０ '])
def test_bad_coordinate(tmp_path,token):
    p=tmp_path/'bad.pdb';p.write_text(PDB[:30]+token+PDB[38:])
    with pytest.raises(ArtifactError):validate_input(p)

def test_valid_alias(tmp_path):
    p=tmp_path/'space; name.ENT';p.write_text(PDB)
    assert validate_input(p)=='pdb'

def test_bounded_child(tmp_path):
    with pytest.raises(ArtifactError,match='timed out'):
        run_bounded([sys.executable,'-c','import time; time.sleep(10)'],tmp_path,timeout=.05)

@pytest.mark.parametrize('pockets',[[],[{'rank':1,'score':float('nan')}],[{'rank':2,'score':.5}]])
def test_invalid_result(pockets):
    with pytest.raises(ArtifactError):validate_pockets(pockets)

def test_no_clobber(tmp_path):
    (tmp_path/'a.pockets.json').write_text('original')
    with pytest.raises(ArtifactError):
        with publication(tmp_path,'a'):pass
    assert (tmp_path/'a.pockets.json').read_text()=='original'

def test_publication_exception(tmp_path):
    with pytest.raises(RuntimeError):
        with publication(tmp_path,'a') as stage:
            (stage/'a.pockets.json').write_text('{}');raise RuntimeError('injected')
    assert not (tmp_path/'a.pockets.json').exists()
    assert list(tmp_path.glob('.a.failed-*'))

def test_publication_complete(tmp_path):
    with publication(tmp_path,'a') as stage:
        (stage/'a_fpocket').mkdir();(stage/'a.pockets.json').write_text('{}')
        (stage/'a.pockets.meta.json').write_text('{}')
    assert (tmp_path/'a.pockets.meta.json').is_file()
    assert (tmp_path/'a_fpocket').is_dir()

def test_insertion_codes_distinct():
    from dde.core.pocket_runtime import residue_records
    a=PDB;b=PDB[:26]+'B'+PDB[27:]
    records=residue_records(a+b,'pdb')
    assert len(records)==2
    assert {r['insertion_code'] for r in records}=={'A','B'}

def test_rollback_partial_publication(tmp_path,monkeypatch):
    import os
    real=os.rename
    def fail(src,dst):
        if Path(dst)==tmp_path/'a.pockets.json':raise OSError('injected disk failure')
        return real(src,dst)
    monkeypatch.setattr(os,'rename',fail)
    with pytest.raises(OSError):
        with publication(tmp_path,'a') as stage:
            (stage/'a_fpocket').mkdir();(stage/'a.pockets.json').write_text('{}')
            (stage/'a.pockets.meta.json').write_text('{}')
    assert not (tmp_path/'a_fpocket').exists()
    assert not (tmp_path/'a.pockets.meta.json').exists()
    assert len(list(tmp_path.glob('.a.failed-*')))==1

def test_same_destination_lock(tmp_path):
    with pytest.raises(RuntimeError):
        with publication(tmp_path,'a'):
            with pytest.raises(ArtifactError,match='another pocket run'):
                with publication(tmp_path,'a'):pass
            raise RuntimeError('abort outer test')

def test_adjacent_negative_pqr_coordinates():
    from dde.core.pocket_runtime import validate_vertices
    row='ATOM      8    O STP    77      -6.783 -39.303-102.796    0.00     3.96'
    validate_vertices([row],1)
