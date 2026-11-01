import os
import unittest
from unittest.mock import patch
from aws_manager import parse_command, aws_env, redact, App

class Tests(unittest.TestCase):
    def test_windows_path(self):
        self.assertEqual(parse_command(r'aws s3 sync s3://example "C:\Users\ExampleUser\My Files"'), ['s3','sync','s3://example',r'C:\Users\ExampleUser\My Files'])
    def test_json(self):
        self.assertEqual(parse_command('ec2 run-instances --tag-specifications \'{"a": "b"}\'')[-1],'{"a": "b"}')
    def test_empty(self):
        with self.assertRaises(ValueError): parse_command('aws')
    def test_invalid_quote(self):
        with self.assertRaises(ValueError): parse_command('s3 ls "abc')
    def test_environment(self):
        with patch.dict(os.environ,{'AWS_ACCESS_KEY_ID':'fake','AWS_SESSION_TOKEN':'fake','AWS_PROFILE':'other'}):
            env=aws_env()
            self.assertNotIn('AWS_ACCESS_KEY_ID',env)
            self.assertNotIn('AWS_SESSION_TOKEN',env)
            self.assertNotIn('AWS_PROFILE',env)
            self.assertEqual(env['AWS_CLI_AUTO_PROMPT'],'off')
    def test_redaction(self):
        self.assertNotIn('test-secret',redact('{"SecretAccessKey": "test-secret"}'))
        self.assertIn('[ACCESS KEY REDACTED]',redact('AKIA'+'A'*16))
    def test_uri(self):
        class Var:
            def __init__(self,v): self.v=v
            def get(self): return self.v
        from types import SimpleNamespace
        for value in ['example','arn:aws:s3:::example','s3://example/']:
            dummy=SimpleNamespace(bucket=Var(value),prefix=Var('folder/'))
            self.assertEqual(App.s3_uri(dummy),('example','s3://example/folder/'))

if __name__=='__main__': unittest.main()
