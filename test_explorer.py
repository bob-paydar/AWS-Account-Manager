import json
import os
from pathlib import Path
import queue
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from explorer import list_args,safe_target,ExplorerApp
from project_store import validate_project,atomic_json,protect,restore_backup

class Tests(unittest.TestCase):
    def test_folder_pagination(self):
        args=list_args('example','a/',False,'next-token')
        self.assertIn('--delimiter',args)
        self.assertEqual(args[-2:],['--continuation-token','next-token'])
        self.assertNotIn('--delimiter',list_args('example','',True))
    def test_safe_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(safe_target(folder,'a/test.html'),Path(folder)/'a/test.html')
            for bad in ['../bad','/absolute','a/../../bad','a\\bad','CON.txt','a/file.','C:/bad']:
                with self.subTest(bad=bad),self.assertRaises(ValueError):safe_target(folder,bad)
    def test_project_roundtrip(self):
        obj={'format':'aws.manager.project','version':1,'settings':{'profile':'sample-profile','recursive':True,'prefix':'folder/'}}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'example.awsproj';atomic_json(path,obj)
            self.assertEqual(validate_project(json.loads(path.read_text())),obj)
        with self.assertRaises(ValueError): validate_project({'format':'aws.manager.project','version':1,'settings':{'profile':123}})
    def test_merge_logins_preserves_other_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'credentials';path.write_text('[keep]\naws_access_key_id = dummy\n[replace]\naws_access_key_id = old\n')
            with patch.dict(os.environ,{'AWS_SHARED_CREDENTIALS_FILE':str(path)}):
                restore_backup({'credentials':'[replace]\naws_access_key_id = new\n'})
            text=path.read_text();self.assertIn('[keep]',text);self.assertIn('new',text);self.assertNotIn('old',text)
    @unittest.skipUnless(os.name=='nt','DPAPI requires Windows')
    def test_dpapi(self):
        data=b'fake test credentials'; self.assertEqual(protect(protect(data),True),data)
    def test_batch_events_and_context(self):
        import threading
        class Var:
            def __init__(self,v):self.v=v
            def get(self):return self.v
            def set(self,v):self.v=v
        calls=[]
        class Proc:
            def __init__(self,cmd,**kwargs):calls.append(cmd);self.stdout=iter(['{}\n'])
            def wait(self):return 0
            def poll(self):return 0
        stub=SimpleNamespace(busy=False,profile=Var('active'),region=Var('us-east-2'),q=queue.Queue(),cancelled=threading.Event(),progress=SimpleNamespace(start=lambda:None),status=Var(''),proc=None)
        with patch('explorer.find_aws',return_value='aws'),patch('explorer.subprocess.Popen',Proc):
            ExplorerApp.batch(stub,[['s3','cp','a','s3://b/a'],['s3','cp','b','s3://b/b']],context=('captured','us-west-2'),refresh=True)
            events=[]
            while True:
                event=stub.q.get(timeout=2);events.append(event)
                if event[0]=='finished':break
        self.assertEqual(len(calls),2)
        self.assertIn('captured',calls[0]);self.assertNotIn('active',calls[0])
        self.assertTrue(events[-1][1][3]);self.assertIsNone(events[-1][1][2])
    def test_completion_clears_busy_before_callback(self):
        called=[];q=queue.Queue()
        stub=SimpleNamespace(q=q,busy=True,pending_refresh=False,progress=SimpleNamespace(stop=lambda:None),status=SimpleNamespace(set=lambda _:None),write=lambda _:None,after=lambda *_:None,poll=lambda:None)
        q.put(('finished',([],lambda _:called.append(stub.busy),None,False)))
        ExplorerApp.poll(stub)
        self.assertEqual(called,[False])

if __name__=='__main__':unittest.main()
