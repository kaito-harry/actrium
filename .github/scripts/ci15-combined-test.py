import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).parent

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

space=module('space','ci15-space-guard.py')
partition=module('partition','ci15-assert-realtime.py')

class GuardTests(unittest.TestCase):
    def test_threshold(self):
        self.assertTrue(space.cleanup_needed(space.MIN_FREE_BYTES-1))
        self.assertFalse(space.cleanup_needed(space.MIN_FREE_BYTES))
        self.assertFalse(space.cleanup_needed(space.MIN_FREE_BYTES+1))
        with self.assertRaises(ValueError):space.cleanup_needed(-1)
    def test_partition(self):
        a={('a','one')};b={('b','two')}
        partition.verify(a|b,a,b)
        for whole,left,right in [(a|b,a,a|b),(a|b,a,{('c','extra')}),(a,a,set())]:
            with self.assertRaises(ValueError):partition.verify(whole,left,right)
    def test_selection_ignores_filtered_and_ignored(self):
        def case(ignored,status):return {'ignored':ignored,'filter-match':{'status':status}}
        d={'rust-suites':{'a':{'binary-id':'id','testcases':{'yes':case(False,'matches'),'no':case(False,'mismatch'),'ignored':case(True,'matches')}}}}
        self.assertEqual(partition.selected(d),{('id','yes')})

if __name__=='__main__':unittest.main()
