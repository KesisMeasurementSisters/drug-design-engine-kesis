# Copyright 2026 Technologies Kesis & Sisters Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tempfile
import unittest
from pathlib import Path
from validation import compare_tree, run, suite

class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.a=self.root/'reference';self.b=self.root/'actual'
        self.a.mkdir();self.b.mkdir()
        self.text='Pocket 1 :\nScore : 0.855\nVolume : 1455.507\nATOM 1 ILE A 110\n'
        for p in (self.a,self.b):
            (p/'info.txt').write_text(self.text);(p/'pocket.pdb').write_text('ATOM 1 ILE A 110\n')
    def test_equal(self): compare_tree(self.a,self.b)
    def test_volume_only(self):
        (self.b/'info.txt').write_text(self.text.replace('1455.507','1440.100'));compare_tree(self.a,self.b)
    def test_truncated(self):
        (self.b/'info.txt').write_text(self.text.rsplit('ATOM',1)[0])
        with self.assertRaises(AssertionError):compare_tree(self.a,self.b)
    def test_missing_volume_record(self):
        (self.b/'info.txt').write_text(self.text.replace('Volume : 1455.507\n',''))
        with self.assertRaises(AssertionError):compare_tree(self.a,self.b)
    def test_missing_pocket(self):
        (self.b/'pocket.pdb').unlink()
        with self.assertRaises(AssertionError):compare_tree(self.a,self.b)
    def test_extra_pocket(self):
        (self.b/'pocket2.pdb').write_text('ATOM 2\n')
        with self.assertRaises(AssertionError):compare_tree(self.a,self.b)
    def test_changed_residue(self):
        (self.b/'pocket.pdb').write_text('ATOM 1 LEU A 110\n')
        with self.assertRaises(AssertionError):compare_tree(self.a,self.b)
    def test_changed_score(self):
        (self.b/'info.txt').write_text(self.text.replace('0.855','0.854'))
        with self.assertRaises(AssertionError):compare_tree(self.a,self.b)
    def test_nonfinite(self):
        for value in ('nan','-inf','Infinity'):
            (self.b/'info.txt').write_text(self.text.replace('1455.507',value))
            with self.assertRaises(AssertionError):compare_tree(self.a,self.b)
    def test_missing_binary_is_failure(self):
        report=suite(self.root/'absent',self.root,self.root/'run')
        self.assertFalse(report['checks'][0]['passed'])
    def test_timeout_is_failure(self):
        import subprocess,sys
        with self.assertRaises(subprocess.TimeoutExpired):run([sys.executable,'-c','import time; time.sleep(2)'],.05)

if __name__=='__main__':unittest.main()
