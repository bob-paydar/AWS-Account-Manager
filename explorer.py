"""Explorer UI additions; original CLI/setup/build behavior retained."""
import json
import os
import queue
import subprocess
import tempfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from aws_manager import App, find_aws, aws_env
from project_store import atomic_json, validate_project, login_backup, decode_backup, restore_backup


def list_args(bucket,prefix,recursive=False,token=None):
    args=['s3api','list-objects-v2','--bucket',bucket,'--prefix',prefix,'--max-keys','1000','--no-paginate']
    if not recursive: args += ['--delimiter','/']
    if token: args += ['--continuation-token',token]
    return args


def safe_target(root,relative):
    import re
    parts=relative.split('/')
    if not parts or any(not p or p in ('.','..') or p.endswith((' ','.')) or re.search(r'[<>:"\\|?*\x00-\x1f]',p) or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',p,re.I) for p in parts):
        raise ValueError('Object key is not a safe Windows path: '+relative)
    base=Path(root).resolve(); target=base.joinpath(*parts).resolve()
    if not target.is_relative_to(base): raise ValueError('Destination escapes selected folder.')
    return target


class ExplorerApp(App):
    def __init__(self):
        self.rows={}; self.checked=set(); self.project_path=None; self.pending_refresh=False
        self.history=[]; self.history_index=-1; self.tempdirs=[]; self.editors=[]
        super().__init__()
        self.title('AWS Account Manager 1.4 | Bob Paydar')
        self.filter=tk.StringVar(); self.recursive=tk.BooleanVar(value=False)
        self.view_mode=tk.StringVar(value='Large icons')
        self.backup_logins=tk.BooleanVar(value=False); self.count=tk.StringVar(value='No folder loaded')
        # Rebuild only the explorer tab, leaving command console and account tools intact.
        s3=self.tree.master.master
        for child in s3.winfo_children(): child.destroy()
        row=ttk.Frame(s3); row.pack(fill='x',pady=(0,6))
        for label,fn in [('Back',self.back),('Up',self.up),('Root',lambda:self.navigate('')),('Refresh files (F5)',self.refresh_files)]:
            ttk.Button(row,text=label,command=fn).pack(side='left',padx=2)
        ttk.Label(row,text='Bucket').pack(side='left',padx=(10,4))
        self.buckets=ttk.Combobox(row,textvariable=self.bucket,width=25); self.buckets.pack(side='left',fill='x',expand=True)
        self.buckets.bind('<<ComboboxSelected>>',lambda _:self.navigate(''))
        ttk.Button(row,text='List buckets',command=self.list_buckets).pack(side='left',padx=4)
        row=ttk.Frame(s3); row.pack(fill='x')
        ttk.Label(row,text='Folder / prefix').pack(side='left')
        address=ttk.Entry(row,textvariable=self.prefix); address.pack(side='left',fill='x',expand=True,padx=6)
        address.bind('<Return>',lambda _:self.browse())
        ttk.Button(row,text='Go',command=self.browse).pack(side='left')
        ttk.Checkbutton(row,text='All subfolders',variable=self.recursive,command=self.browse).pack(side='left',padx=6)
        row=ttk.Frame(s3); row.pack(fill='x',pady=6)
        for label,fn in [('Select all',lambda:self.selection_action('all')),('Select none',lambda:self.selection_action('none')),('Invert',lambda:self.selection_action('invert'))]:
            ttk.Button(row,text=label,command=fn).pack(side='left',padx=2)
        ttk.Label(row,text='Filter loaded items').pack(side='left',padx=(12,4))
        ttk.Entry(row,textvariable=self.filter).pack(side='left',fill='x',expand=True)
        ttk.Button(row,text='Load more',command=lambda:self.browse(True)).pack(side='left',padx=4)
        from file_views import FileView, VIEWS
        from picture_browser import Pictures
        ttk.Label(row,text='View').pack(side='left',padx=4)
        chooser=ttk.Combobox(row,textvariable=self.view_mode,values=VIEWS,state='readonly',width=18)
        chooser.pack(side='left')
        self.tree=FileView(s3,self); self.tree.pack(fill='both',expand=True)
        self.pictures=Pictures(self)
        self.view_mode.trace_add('write',lambda *_:self.tree.schedule())
        ttk.Label(s3,textvariable=self.count).pack(anchor='w',pady=3)
        row=ttk.Frame(s3); row.pack(fill='x')
        ttk.Label(row,text='Local folder').pack(side='left'); ttk.Entry(row,textvariable=self.destination).pack(side='left',fill='x',expand=True,padx=5)
        ttk.Button(row,text='Choose',command=self.choose_folder).pack(side='left')
        actions=ttk.Frame(s3); actions.pack(fill='x',pady=5)
        for i,(label,fn) in enumerate([('Upload files',self.upload),('Download selected',self.download_selected),('Edit file',self.edit_file),('Delete selected',self.delete),('Preview sync',lambda:self.sync(True)),('Download folder',self.sync),('New folder',self.new_folder),('Copy S3 path',self.copy_path)]):
            ttk.Button(actions,text=label,command=fn).grid(row=i//4,column=i%4,sticky='ew',padx=2,pady=2)
            actions.columnconfigure(i%4,weight=1)
        self.filter.trace_add('write',lambda *_:self.render())
        menu=tk.Menu(self); self.config(menu=menu); project=tk.Menu(menu,tearoff=False); menu.add_cascade(label='Project',menu=project)
        for label,fn in [('New project',self.new_project),('Open project…',self.open_project),('Save project',self.save_project),('Save project as…',lambda:self.save_project(True))]: project.add_command(label=label,command=fn)
        project.add_separator(); project.add_checkbutton(label='Include encrypted AWS login backup (this Windows user)',variable=self.backup_logins)
        view=tk.Menu(menu,tearoff=False); menu.add_cascade(label='View',menu=view); view.add_command(label='Refresh files (F5)',command=self.refresh_files)
        view.add_separator()
        for mode in VIEWS: view.add_radiobutton(label=mode,variable=self.view_mode,value=mode)
        from help_window import install_help
        install_help(self,menu)
        self.bind('<F5>',lambda _:self.refresh_files()); self.bind('<Control-s>',lambda _:self.save_project()); self.bind('<Control-o>',lambda _:self.open_project())
        for widget in self.winfo_children(): self.rename_refresh(widget)
        self.write('v1.1: F5 refreshes S3 files. Upload/edit/delete automatically reload the current folder.\n')

    def rename_refresh(self,widget):
        if isinstance(widget,ttk.Button) and widget.cget('text')=='Refresh': widget.configure(text='Refresh profiles')
        for child in widget.winfo_children(): self.rename_refresh(child)

    def context(self):
        bucket,_=self.s3_uri()
        return (self.profile.get().strip(),self.region.get().strip(),bucket,self.prefix.get(),self.recursive.get())

    def run(self,args,callback=None,global_args=True):
        self.batch([args],lambda results:callback(results[0]) if callback else None,global_args)

    def batch(self,commands,callback=None,global_args=True,context=None,refresh=False):
        if self.busy: messagebox.showinfo('Busy','Wait for the current operation or press Stop.'); return
        aws=find_aws()
        if not aws: self.initial(); return
        profile,region=context[:2] if context else (self.profile.get().strip(),self.region.get().strip())
        if not profile: messagebox.showerror('Profile','Choose an AWS profile.'); return
        commands=[list(c) for c in commands]
        self.busy=True; self.cancelled.clear(); self.progress.start(); self.status.set(f'Running {len(commands)} operation(s)…')
        def worker():
            results=[]; error=None
            try:
                for number,args in enumerate(commands,1):
                    if self.cancelled.is_set(): raise RuntimeError('Cancelled. Completed actions are not rolled back.')
                    cmd=[aws]+args
                    if global_args:
                        cmd += ['--profile',profile,'--output','json','--no-cli-pager','--no-cli-auto-prompt']
                        if region: cmd += ['--region',region]
                    self.q.put(('text',f'\n[{number}/{len(commands)}] '+ ' '.join(args[:2])+f' | {profile}\n'))
                    self.proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,text=True,encoding='utf-8',errors='replace',env=aws_env(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    if self.cancelled.is_set(): self.proc.terminate()
                    lines=[]; size=0
                    for line in self.proc.stdout:
                        if callback:
                            size+=len(line)
                            if size>16_000_000: raise RuntimeError('Response too large. Narrow the query.')
                            lines.append(line)
                        self.q.put(('text',line))
                    rc=self.proc.wait()
                    if rc: raise RuntimeError(f'Command exited with code {rc}. See AWS output above. {len(results)} operation(s) completed.')
                    results.append(''.join(lines))
                if self.cancelled.is_set(): raise RuntimeError('Cancelled.')
            except Exception as exc:
                error=str(exc)
                if self.proc and self.proc.poll() is None: self.proc.terminate(); self.proc.wait()
            finally:
                self.proc=None
                self.q.put(('finished',(results,callback,error,refresh)))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        for _ in range(250):
            try: kind,data=self.q.get_nowait()
            except queue.Empty: break
            if kind=='text': self.write(data)
            elif kind=='done': self.busy=False; self.progress.stop(); self.status.set('Ready')
            elif kind=='finished':
                results,callback,error,refresh=data
                self.busy=False; self.progress.stop()
                self.status.set('Failed — see output' if error else 'Completed')
                self.write(('ERROR: '+error if error else 'Completed successfully.')+'\n')
                if not error and callback:
                    try: callback(results)
                    except Exception as exc: self.write(f'Processing error: {exc}\n'); messagebox.showerror('Result',str(exc))
                if refresh: self.pending_refresh=True
        if self.pending_refresh and not self.busy:
            self.pending_refresh=False
            if self.bucket.get().strip(): self.browse()
        self.after(80,self.poll)

    def refresh_files(self):
        if self.busy: self.pending_refresh=True; self.status.set('File refresh queued'); return
        self.pictures.failed.clear()
        self.browse()

    def browse(self,next_page=False):
        if self.busy: self.pending_refresh=True; return
        try: context=self.context()
        except ValueError as exc: messagebox.showerror('Bucket',str(exc)); return
        if next_page and (not self.token or getattr(self,'page_context',None)!=context):
            messagebox.showinfo('Pagination','No additional page is available.'); return
        token=self.token if next_page else None
        def display(text):
            if self.context()!=context: self.pending_refresh=True; return
            obj=json.loads(text)
            if not next_page: self.rows.clear(); self.checked.clear()
            self.page_context=context; self.token=obj.get('NextContinuationToken')
            for item in obj.get('CommonPrefixes',[]):
                key=item['Prefix']; self.rows['d:'+key]={'key':key,'kind':'Folder','size':0,'modified':''}
            for item in obj.get('Contents',[]):
                key=item['Key']
                if key==context[3] and key.endswith('/'): continue
                self.rows['f:'+key]={'key':key,'kind':'File','size':item['Size'],'modified':item.get('LastModified','')}
            self.render()
            loc=(context[2],context[3])
            if not next_page and (self.history_index<0 or self.history[self.history_index]!=loc):
                self.history=self.history[:self.history_index+1]+[loc]; self.history_index+=1
        self.run(list_args(context[2],context[3],context[4],token),display)

    def render(self):
        if not hasattr(self,'filter'): return
        highlighted=set(self.tree.selection()); self.tree.delete(*self.tree.get_children())
        needle=self.filter.get().casefold(); prefix=self.prefix.get()
        for ident,item in self.rows.items():
            if needle not in item['key'].casefold(): continue
            name=item['key'][len(prefix):] if item['key'].startswith(prefix) else item['key']
            self.tree.insert('', 'end',iid=ident,values=('☑' if ident in self.checked else '☐',name,item['kind'],item['size'] if item['kind']=='File' else '',item['modified']))
        self.tree.selection_set([i for i in highlighted if self.tree.exists(i)])
        self.count.set(f'{len(self.tree.get_children())} visible / {len(self.rows)} loaded • {len(self.checked)} checked'+(' • More available: Load more' if self.token else ''))

    def sort_rows(self,col):
        mapping={'name':'key','kind':'kind','size':'size','modified':'modified'}
        if col=='check': self.selection_action('invert'); return
        reverse=getattr(self,'sort_state',None)==(col,False); self.sort_state=(col,reverse)
        self.rows=dict(sorted(self.rows.items(),key=lambda pair:pair[1][mapping[col]],reverse=reverse)); self.render()

    def selection_action(self,action):
        visible=set(self.tree.get_children())
        if action=='all': self.checked |= visible
        elif action=='none': self.checked.clear(); self.tree.selection_remove(*self.tree.selection())
        else: self.checked ^= visible
        self.render(); return 'break'

    def check_click(self,event):
        ident=self.tree.identify_row(event.y)
        if ident and self.tree.identify_column(event.x)=='#1':
            self.checked.symmetric_difference_update({ident}); self.render(); return 'break'

    def check_highlight(self,event=None):
        self.checked.symmetric_difference_update(set(self.tree.selection())); self.render(); return 'break'

    def chosen(self,files_only=False):
        if self.context()!=getattr(self,'page_context',None): raise ValueError('Location or account changed. Refresh files first.')
        ids=self.checked or set(self.tree.selection())
        if not ids: raise ValueError('Check files or select rows first.')
        items=[self.rows[i] for i in ids if i in self.rows]
        if files_only and any(i['kind']=='Folder' or i['key'].endswith('/') for i in items):
            raise ValueError('Select files only for this action. Open a folder to manage its contents.')
        return items

    def navigate(self,prefix):
        self.prefix.set(prefix); self.filter.set(''); self.browse()

    def back(self):
        if self.history_index>0:
            self.history_index-=1; bucket,prefix=self.history[self.history_index]; self.bucket.set(bucket); self.navigate(prefix)

    def up(self):
        current=self.prefix.get().rstrip('/'); self.navigate(current.rsplit('/',1)[0]+'/' if '/' in current else '')

    def activate(self,event=None):
        if event and getattr(event,'x',None) is not None and self.tree.identify_column(event.x)=='#1': return
        ids=self.tree.selection()
        if len(ids)==1:
            item=self.rows[ids[0]]
            if item['kind']=='Folder': self.navigate(item['key'])
            elif __import__('file_views').is_picture(item['key']): self.preview_picture(ids[0])
            else: self.edit_file(ids[0])
        return 'break'

    def context_menu(self,event):
        ident=self.tree.identify_row(event.y)
        if not ident: return
        if ident not in self.tree.selection(): self.tree.selection_set(ident)
        menu=tk.Menu(self,tearoff=False)
        for label,fn in [('Open / edit',self.activate),('Download selection',self.download_selected),('Delete selection',self.delete),('Copy S3 path',self.copy_path),('Refresh',self.refresh_files)]: menu.add_command(label=label,command=fn)
        menu.tk_popup(event.x_root,event.y_root)

    def copy_path(self):
        try: items=self.chosen(); bucket=self.context()[2]
        except ValueError as exc: messagebox.showerror('Selection',str(exc)); return
        self.clipboard_clear(); self.clipboard_append('\n'.join('s3://'+bucket+'/'+i['key'] for i in items))

    def upload(self):
        try: context=self.context()
        except ValueError as exc: messagebox.showerror('Bucket',str(exc)); return
        files=filedialog.askopenfilenames(title='Select files to upload')
        if not files: return
        prefix=context[3]
        if prefix and not prefix.endswith('/'): prefix+='/'
        if not messagebox.askyesno('Upload files',f'Upload {len(files)} files to s3://{context[2]}/{prefix}?\nMatching object names will be replaced.'): return
        self.prefix.set(prefix); self.filter.set('')
        commands=[['s3','cp',p,'s3://'+context[2]+'/'+prefix+Path(p).name,'--no-progress'] for p in files]
        self.batch(commands,context=context,refresh=True)

    def download_selected(self):
        try:
            items=self.chosen(True); context=self.context()
            folder=filedialog.askdirectory(initialdir=self.destination.get(),title='Download selected files into')
            if not folder:return
            self.destination.set(folder)
            targets=[safe_target(folder,i['key'][len(context[3]):]) for i in items]
            if len({str(t).casefold() for t in targets})!=len(targets): raise ValueError('Some keys collide on Windows (case-insensitive names). Download separately.')
            if not messagebox.askyesno('Download',f'Download {len(items)} files to {folder}?\nExisting local files may be replaced.'):return
            for t in targets: t.parent.mkdir(parents=True,exist_ok=True)
            self.batch([['s3','cp','s3://'+context[2]+'/'+i['key'],str(t),'--no-progress'] for i,t in zip(items,targets)],context=context)
        except (ValueError,OSError) as exc: messagebox.showerror('Download',str(exc))

    def delete(self):
        try: items=self.chosen(True); context=self.context()
        except ValueError as exc: messagebox.showerror('Selection',str(exc)); return
        names='\n'.join(i['key'] for i in items[:8])
        if simpledialog.askstring('Delete files',f'Delete {len(items)} files from {context[2]}?\n{names}\n\nType DELETE to confirm:')!='DELETE': return
        self.batch([['s3api','delete-object','--bucket',context[2],'--key',i['key']] for i in items],context=context,refresh=True)

    def new_folder(self):
        try: context=self.context()
        except ValueError as exc: messagebox.showerror('Bucket',str(exc)); return
        name=simpledialog.askstring('New folder','Folder name (one level):')
        if not name:return
        if name in ('.','..') or any(c in name for c in '/\\'): messagebox.showerror('Name','Enter one folder name.'); return
        key=context[3].rstrip('/')+('/' if context[3] else '')+name+'/'
        self.batch([['s3api','put-object','--bucket',context[2],'--key',key,'--if-none-match','*']],context=context,refresh=True)

    def edit_file(self,ident=None):
        try:
            context=self.context()
            if context!=getattr(self,'page_context',None): raise ValueError('Refresh this location first.')
            items=[self.rows[ident]] if ident else self.chosen(True)
            if len(items)!=1: raise ValueError('Select exactly one file to edit.')
            item=items[0]
            if item['kind']!='File': raise ValueError('Select a text file.')
            if item['size']>5*1024*1024: raise ValueError('Built-in editor supports text files up to 5 MB. Download larger files to edit locally.')
        except ValueError as exc: messagebox.showerror('Edit',str(exc)); return
        folder=tempfile.TemporaryDirectory(prefix='aws-edit-'); self.tempdirs.append(folder); target=Path(folder.name)/'content'
        def downloaded(results):
            metadata=json.loads(results[0]); data=target.read_bytes()
            if len(data)>5*1024*1024 or b'\x00' in data: raise ValueError('This file is binary or exceeds 5 MB. Use Download instead.')
            try: content=data.decode('utf-8-sig')
            except UnicodeDecodeError: raise ValueError('Editor supports UTF-8 text. Download this file to use another editor.')
            newline='\r\n' if b'\r\n' in data else '\n'; bom=data.startswith(b'\xef\xbb\xbf')
            self.editor(context,item['key'],content.replace('\r\n','\n'),metadata,target,newline,bom)
        self.batch([['s3api','get-object','--bucket',context[2],'--key',item['key'],str(target)]],downloaded,context=context)

    def editor(self,context,key,content,metadata,target,newline,bom):
        win=tk.Toplevel(self); self.editors.append(win); win.title('Edit — '+key); win.geometry('950x680')
        ttk.Label(win,text=f'Profile: {context[0]}   |   s3://{context[2]}/{key}',padding=8).pack(anchor='w')
        row=ttk.Frame(win); row.pack(fill='x',padx=8)
        status=tk.StringVar(value='UTF-8 • Save to S3 replaces this object only if it has not changed remotely.')
        text=tk.Text(win,undo=True,wrap='none',font=('Consolas',11)); text.pack(fill='both',expand=True,padx=8,pady=8)
        text.insert('1.0',content); text.edit_modified(False)
        bar=ttk.Scrollbar(win,orient='horizontal',command=text.xview); bar.pack(fill='x',padx=8); text.configure(xscrollcommand=bar.set)
        ttk.Label(win,textvariable=status,padding=8).pack(anchor='w')
        keep_tags=tk.BooleanVar(value=False)
        ttk.Checkbutton(row,text='Preserve tags (needs tagging permissions)',variable=keep_tags).pack(side='right')
        def bytes_now(): return (b'\xef\xbb\xbf' if bom else b'')+text.get('1.0','end-1c').replace('\n',newline).encode('utf-8')
        def save_local():
            name=filedialog.asksaveasfilename(parent=win,initialfile=key.rsplit('/',1)[-1])
            if name:
                try: Path(name).write_bytes(bytes_now()); status.set('Local copy saved.')
                except OSError as exc: messagebox.showerror('Save',str(exc),parent=win)
        def save_remote():
            if self.busy: messagebox.showinfo('Busy','Wait for current operation.',parent=win); return
            if not metadata.get('ETag'): messagebox.showerror('Save','Missing ETag; reopen the file.',parent=win); return
            if not messagebox.askyesno('Save to S3',f'Replace s3://{context[2]}/{key}\nusing profile {context[0]}?\n'+('Object tags will be preserved.' if keep_tags.get() else 'Object tags are not retained unless Preserve tags is checked.'),parent=win): return
            try: target.write_bytes(bytes_now())
            except OSError as exc: messagebox.showerror('Save',str(exc),parent=win); return
            snapshot=text.get('1.0','end-1c')
            args=['s3api','put-object','--bucket',context[2],'--key',key,'--body',str(target),'--if-match',metadata['ETag']]
            for field,option in [('ContentType','--content-type'),('CacheControl','--cache-control'),('ContentDisposition','--content-disposition'),('ContentEncoding','--content-encoding'),('ContentLanguage','--content-language'),('WebsiteRedirectLocation','--website-redirect-location'),('ServerSideEncryption','--server-side-encryption'),('SSEKMSKeyId','--ssekms-key-id')]:
                if metadata.get(field): args += [option,metadata[field]]
            if metadata.get('Metadata'): args += ['--metadata',json.dumps(metadata['Metadata'])]
            # Preserve tags; requires GetObjectTagging/PutObjectTagging when editing.
            def tags_loaded(results):
                from urllib.parse import urlencode
                tags=json.loads(results[0]).get('TagSet',[])
                upload_args=args+(['--tagging',urlencode([(t['Key'],t['Value']) for t in tags])] if tags else [])
                def saved(outputs):
                    metadata['ETag']=json.loads(outputs[0])['ETag']
                    if win.winfo_exists():
                        if text.get('1.0','end-1c')==snapshot: text.edit_modified(False)
                        status.set('Saved to S3. Current folder refresh requested.')
                self.batch([upload_args],saved,context=context,refresh=True)
            if keep_tags.get():
                self.batch([['s3api','get-object-tagging','--bucket',context[2],'--key',key]],tags_loaded,context=context)
            else:
                tags_loaded(['{"TagSet": []}'])
        def close_editor():
            if text.edit_modified() and not messagebox.askyesno('Unsaved edits','Close without saving these edits?',parent=win): return
            win.destroy()
        ttk.Button(row,text='Save to S3',command=save_remote).pack(side='left')
        ttk.Button(row,text='Save local copy',command=save_local).pack(side='left',padx=6)
        ttk.Button(row,text='Undo',command=lambda:text.edit_undo() if text.tk.getboolean(text.tk.call(text._w,'edit','canundo')) else None).pack(side='left')
        win.bind('<Control-s>',lambda e:(save_remote(),'break')[1]); win.protocol('WM_DELETE_WINDOW',close_editor)

    def settings(self):
        return {**{name:getattr(self,name).get() for name in ('profile','region','bucket','prefix','destination','output_format','filter','recursive','view_mode')},'geometry':self.geometry()}

    def save_project(self,save_as=False):
        path=self.project_path
        if save_as or not path: path=filedialog.asksaveasfilename(defaultextension='.awsproj',filetypes=[('AWS Manager project','*.awsproj')])
        if not path:return
        try:
            obj={'format':'aws.manager.project','version':1,'settings':self.settings()}
            if self.backup_logins.get(): obj['login_backup']=login_backup()
            atomic_json(path,obj); self.project_path=path; self.title('AWS Account Manager 1.4 — '+Path(path).name+' | Bob Paydar')
            self.status.set('Project saved'+(' with encrypted login backup' if 'login_backup' in obj else ' (AWS profiles remain saved by AWS CLI)'))
        except Exception as exc: messagebox.showerror('Save project',str(exc))

    def open_project(self):
        if self.busy: messagebox.showinfo('Busy','Wait for current operation before changing projects.'); return
        path=filedialog.askopenfilename(filetypes=[('AWS Manager project','*.awsproj')])
        if not path:return
        try:
            if Path(path).stat().st_size>8_000_000: raise ValueError('Project is too large.')
            obj=validate_project(json.loads(Path(path).read_text(encoding='utf-8')))
            if obj.get('login_backup') and messagebox.askyesno('Restore login backup','Restore encrypted AWS configuration and credentials?\nMatching profile sections will be replaced; other profiles remain.\nOnly restore projects you trust. This requires the original Windows user/computer.\nSSO browser sessions may still require signing in again.'):
                restore_backup(decode_backup(obj['login_backup']))
            settings=obj['settings']
            self.view_mode.set('Large icons')
            for name in ('profile','region','bucket','prefix','destination','output_format','filter','recursive','view_mode'):
                if name in settings:getattr(self,name).set(settings[name])
            geometry=settings.get('geometry','')
            import re
            if re.fullmatch(r'\d+x\d+(?:[+-]\d+[+-]\d+)?',geometry): self.geometry(geometry)
            self.backup_logins.set(bool(obj.get('login_backup'))); self.project_path=path
            self.rows.clear(); self.checked.clear(); self.token=None; self.history=[]; self.history_index=-1; self.render()
            self.title('AWS Account Manager 1.4 — '+Path(path).name+' | Bob Paydar')
            self.refresh_profiles(); self.pending_refresh=bool(self.bucket.get())
        except Exception as exc: messagebox.showerror('Open project',str(exc))

    def new_project(self):
        if self.busy: messagebox.showinfo('Busy','Wait for the current operation.'); return
        if not messagebox.askyesno('New project','Reset the current project settings? Save your current project first if needed.'):return
        self.view_mode.set('Large icons')
        self.project_path=None; self.bucket.set(''); self.prefix.set(''); self.filter.set(''); self.recursive.set(False)
        self.rows.clear(); self.checked.clear(); self.token=None; self.history=[]; self.history_index=-1; self.render()
        self.title('AWS Account Manager 1.4 | Bob Paydar')

    def close(self):
        if any(w.winfo_exists() for w in self.editors):
            if not messagebox.askyesno('Close editors','Close the application and all editors? Unsaved editor changes will be lost.'):return
        if self.busy and not messagebox.askyesno('Exit','Stop the current operation and exit? Completed changes cannot be undone.'):return
        self.pictures.close()
        self.stop()
        # Temporary editor files are removed when no worker still uses them.
        if not self.busy:
            for folder in self.tempdirs: folder.cleanup()
        self.destroy()

    def picture_asset(self,ident,size):
        image=self.pictures.request(ident)
        if image is None:return None
        from PIL import Image
        thumb=image.copy();thumb.thumbnail((size,size),Image.Resampling.LANCZOS);return thumb

    def preview_picture(self,ident):
        self.pictures.request(ident,preview=True)
