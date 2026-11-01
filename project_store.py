"""Versioned project settings and optional Windows-user encrypted login backup."""
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile

FIELDS=('profile','region','bucket','prefix','destination','output_format','filter','recursive','geometry','view_mode')

def atomic_json(path, value):
    path=Path(path)
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream: json.dump(value,stream,indent=2)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def validate_project(obj):
    if not isinstance(obj,dict) or obj.get('format') not in ('aws.manager.project','bob.aws.project') or obj.get('version')!=1:
        raise ValueError('Not a supported AWS Manager project.')
    settings=obj.get('settings')
    if not isinstance(settings,dict): raise ValueError('Project settings missing.')
    for name in FIELDS:
        if name in settings and not isinstance(settings[name],bool if name=='recursive' else str):
            raise ValueError('Invalid project field: '+name)
    if settings.get('view_mode','Large icons') not in ('Extra large icons','Large icons','Medium icons','Small icons','List','Details','Tiles'):
        raise ValueError('Invalid file view.')
    if 'login_backup' in obj and not isinstance(obj['login_backup'],str): raise ValueError('Invalid encrypted login backup.')
    return obj

def protect(data, decrypt=False):
    if os.name!='nt': raise RuntimeError('Login backup requires Windows DPAPI.')
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    source=ctypes.create_string_buffer(data); inp=Blob(len(data),ctypes.cast(source,ctypes.POINTER(ctypes.c_ubyte))); out=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True); kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p]; kernel.LocalFree.restype=ctypes.c_void_p
    if decrypt:
        func=crypt.CryptUnprotectData
        func.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        args=(ctypes.byref(inp),None,None,None,None,1,ctypes.byref(out))
    else:
        func=crypt.CryptProtectData
        func.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        args=(ctypes.byref(inp),'AWS Manager login backup',None,None,None,1,ctypes.byref(out))
    func.restype=wintypes.BOOL
    if not func(*args): raise ctypes.WinError(ctypes.get_last_error())
    try: return ctypes.string_at(out.data,out.size)
    finally: kernel.LocalFree(ctypes.cast(out.data,ctypes.c_void_p))

def aws_files():
    return {name:Path(os.environ.get(env,str(Path.home()/'.aws'/name))) for name,env in [('config','AWS_CONFIG_FILE'),('credentials','AWS_SHARED_CREDENTIALS_FILE')]}

def login_backup():
    payload={name:path.read_text(encoding='utf-8') for name,path in aws_files().items() if path.exists()}
    return base64.b64encode(protect(json.dumps(payload).encode())).decode('ascii')

def decode_backup(text):
    obj=json.loads(protect(base64.b64decode(text,validate=True),True))
    if not isinstance(obj,dict) or any(k not in ('config','credentials') or not isinstance(v,str) for k,v in obj.items()):
        raise ValueError('Invalid backup contents.')
    return obj

def restore_backup(payload):
    import configparser
    # Validate both files before writing either; preserve profiles absent from backup.
    staged=[]
    for name,text in payload.items():
        incoming=configparser.RawConfigParser(); incoming.read_string(text)
        if incoming.defaults(): raise ValueError('DEFAULT sections are not supported in AWS backup files.')
        target=aws_files()[name]; merged=configparser.RawConfigParser()
        if target.exists(): merged.read(target,encoding='utf-8')
        for section in incoming.sections():
            if merged.has_section(section): merged.remove_section(section)
            merged.add_section(section)
            for key,value in incoming.items(section): merged.set(section,key,value)
        staged.append((target,merged))
    for target,merged in staged:
        target.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(dir=target.parent,prefix='.aws-restore-')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as stream: merged.write(stream)
            os.replace(temp,target)
        finally:
            if os.path.exists(temp): os.unlink(temp)
