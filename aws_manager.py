"""AWS Account Manager — Bob Paydar. Python 3.10+ / AWS CLI v2."""
import os
import sys
import re
import json
import shlex
import shutil
import queue
import threading
import subprocess
import tempfile
import urllib.request
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog


def find_aws():
    candidates = [shutil.which('aws')]
    for base in (os.environ.get('ProgramFiles', ''), os.environ.get('LOCALAPPDATA', '') + '/Programs'):
        candidates.append(str(Path(base) / 'Amazon/AWSCLIV2/aws.exe'))
    return next((p for p in candidates if p and Path(p).is_file()), None)


def parse_command(value):
    # Windows paths remain literal; double quotes group arguments, JSON single quotes supported.
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ''
    lexer.commenters = ''
    parts = list(lexer)
    if parts and parts[0].lower() in ('aws', 'aws.exe'):
        parts.pop(0)
    if not parts:
        raise ValueError('Enter an AWS command.')
    return parts


def aws_env():
    env = os.environ.copy()
    # Explicit profiles must not accidentally use a different account's environment keys.
    for name in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN', 'AWS_DEFAULT_PROFILE', 'AWS_PROFILE'):
        env.pop(name, None)
    env.update(AWS_PAGER='', AWS_CLI_AUTO_PROMPT='off', PYTHONIOENCODING='utf-8')
    return env


def redact(text):
    text = re.sub(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b', '[ACCESS KEY REDACTED]', text)
    return re.sub(r'(?i)("(?:SecretAccessKey|SessionToken|Password|SecretString|SecretBinary|aws_secret_access_key)"\s*:\s*)"[^"\n]*"', r'\1"[REDACTED]"', text)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('AWS Account Manager | Bob Paydar')
        self.geometry('1150x780'); self.minsize(850, 600)
        self.q = queue.Queue(); self.proc = None; self.busy = False
        self.cancelled = threading.Event(); self.aws = find_aws(); self.token = None
        self.profile = tk.StringVar(value='default'); self.region = tk.StringVar(value='')
        self.status = tk.StringVar(value='Ready'); self.bucket = tk.StringVar()
        self.prefix = tk.StringVar(); self.destination = tk.StringVar(value=str(Path.home() / 'Downloads' / 'S3-Backup'))
        self.command = tk.StringVar(value='sts get-caller-identity'); self.output_format = tk.StringVar(value='json')
        self.identity = tk.StringVar(value='Account not verified — click Verify account')
        style = ttk.Style(self); style.theme_use('clam')
        style.configure('TButton', padding=(10, 6)); style.configure('Treeview', rowheight=25)
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'))
        outer = ttk.Frame(self, padding=12); outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='AWS Account Manager', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Profiles • S3 transfers • AWS service commands').pack(anchor='w', pady=(0, 10))
        bar = ttk.Frame(outer); bar.pack(fill='x')
        ttk.Label(bar, text='Profile').pack(side='left')
        self.profiles = ttk.Combobox(bar, textvariable=self.profile, width=23); self.profiles.pack(side='left', padx=6)
        ttk.Label(bar, text='Region').pack(side='left')
        ttk.Entry(bar, textvariable=self.region, width=18).pack(side='left', padx=6)
        for label, command in [('Refresh', self.refresh_profiles), ('Verify account', lambda: self.run(['sts','get-caller-identity'], self.show_identity)), ('Setup / Login', self.setup)]:
            ttk.Button(bar, text=label, command=command).pack(side='left', padx=3)
        ttk.Label(outer, textvariable=self.identity).pack(anchor='w', pady=8)
        self.profile.trace_add('write', lambda *_: self.identity.set('Account not verified — click Verify account'))
        panes = ttk.Panedwindow(outer, orient='vertical'); panes.pack(fill='both', expand=True)
        tabs = ttk.Notebook(panes); panes.add(tabs, weight=3)
        s3 = ttk.Frame(tabs, padding=10); tabs.add(s3, text='S3 Explorer')
        row = ttk.Frame(s3); row.pack(fill='x')
        ttk.Label(row, text='Bucket').pack(side='left')
        self.buckets = ttk.Combobox(row, textvariable=self.bucket, width=30); self.buckets.pack(side='left', padx=6)
        ttk.Button(row, text='List buckets', command=self.list_buckets).pack(side='left')
        ttk.Label(row, text='Prefix').pack(side='left', padx=(12, 0))
        ttk.Entry(row, textvariable=self.prefix).pack(side='left', fill='x', expand=True, padx=6)
        ttk.Button(row, text='Browse', command=self.browse).pack(side='left')
        ttk.Button(row, text='Next page', command=lambda: self.browse(True)).pack(side='left', padx=4)
        frame = ttk.Frame(s3); frame.pack(fill='both', expand=True, pady=8)
        self.tree = ttk.Treeview(frame, columns=('key','size','modified'), show='headings', selectmode='browse')
        for col, title, width in [('key','Object key',550),('size','Bytes',100),('modified','Modified',190)]:
            self.tree.heading(col, text=title); self.tree.column(col, width=width)
        scroll = ttk.Scrollbar(frame, command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True); scroll.pack(side='right', fill='y')
        row = ttk.Frame(s3); row.pack(fill='x')
        ttk.Label(row, text='Local folder').pack(side='left')
        ttk.Entry(row, textvariable=self.destination).pack(side='left', fill='x', expand=True, padx=6)
        ttk.Button(row, text='Choose', command=self.choose_folder).pack(side='left')
        row = ttk.Frame(s3); row.pack(fill='x', pady=7)
        for label, command in [('Preview download', lambda: self.sync(True)), ('Download bucket / prefix', self.sync), ('Download selected', self.download_selected), ('Upload file', self.upload), ('Delete selected', self.delete)]:
            ttk.Button(row, text=label, command=command).pack(side='left', padx=2)
        ttk.Label(s3, text='Browse shows up to 1,000 objects per page. Sync downloads all matching objects. No sync deletion.').pack(anchor='w')
        console = ttk.Frame(tabs, padding=12); tabs.add(console, text='AWS Command Console')
        ttk.Label(console, text='Run any installed AWS CLI service command using the selected profile and region.').pack(anchor='w')
        ttk.Label(console, text='Examples: ec2 describe-instances  |  lambda list-functions  |  cloudfront list-distributions').pack(anchor='w', pady=8)
        ttk.Entry(console, textvariable=self.command, font=('Consolas', 11)).pack(fill='x', pady=8)
        row = ttk.Frame(console); row.pack(fill='x')
        ttk.Combobox(row, textvariable=self.output_format, values=['json','table','text','yaml','yaml-stream'], width=12, state='readonly').pack(side='left')
        ttk.Button(row, text='Run command…', command=self.custom).pack(side='left', padx=8)
        ttk.Button(row, text='AWS CLI documentation', command=lambda: webbrowser.open('https://docs.aws.amazon.com/cli/latest/reference/')).pack(side='left')
        ttk.Label(console, text='Commands run directly, without a shell. Pipes and PowerShell scripts are not supported.\nUse Setup / Login for interactive commands. Output can contain account data; review before sharing.\nPermissions depend on the selected AWS profile. This app cannot bypass IAM policies.').pack(anchor='w', pady=15)
        logpanel = ttk.Frame(panes); panes.add(logpanel, weight=2)
        row = ttk.Frame(logpanel); row.pack(fill='x')
        ttk.Label(row, text='Activity and command output').pack(side='left')
        ttk.Button(row, text='Stop', command=self.stop).pack(side='right')
        ttk.Button(row, text='Clear', command=lambda: self.log.delete('1.0','end')).pack(side='right')
        ttk.Button(row, text='Export output', command=self.export).pack(side='right')
        self.log = tk.Text(logpanel, wrap='none', height=12, bg='#101c2c', fg='#dce9f7', insertbackground='white', font=('Consolas',10))
        ys = ttk.Scrollbar(logpanel, command=self.log.yview); self.log.configure(yscrollcommand=ys.set)
        ys.pack(side='right', fill='y'); self.log.pack(fill='both', expand=True)
        self.progress = ttk.Progressbar(outer, mode='indeterminate'); self.progress.pack(fill='x', pady=(6, 0))
        row = ttk.Frame(outer); row.pack(fill='x'); ttk.Label(row,textvariable=self.status).pack(side='left')
        ttk.Label(row,text='Programmer: Bob Paydar').pack(side='right')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(80, self.poll); self.after(200, self.initial)

    def initial(self):
        if not self.aws:
            if messagebox.askyesno('AWS CLI missing','AWS CLI v2 was not found. Download and open the official Windows installer now?'):
                self.install_cli()
        else:
            self.refresh_profiles()

    def install_cli(self):
        if self.busy: return
        self.busy = True; self.progress.start(); self.status.set('Downloading AWS CLI installer…')
        def work():
            try:
                folder = Path(tempfile.mkdtemp(prefix='aws-cli-setup-'))
                target = folder / 'AWSCLIV2.msi'
                with urllib.request.urlopen('https://awscli.amazonaws.com/AWSCLIV2.msi', timeout=60) as src, target.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
                # Visible Windows Installer supplies installation and UAC prompts.
                code = subprocess.call(['msiexec.exe','/i',str(target)])
                self.q.put(('text',f'Installer exit code: {code}. Click Refresh after installation.\n'))
            except Exception as exc: self.q.put(('text',f'Installation failed: {exc}\n'))
            finally: self.q.put(('done',None))
        threading.Thread(target=work,daemon=True).start()

    def write(self, text):
        self.log.insert('end', redact(text)); self.log.see('end')
        if int(self.log.index('end-1c').split('.')[0]) > 12000: self.log.delete('1.0','2000.0')

    def run(self, args, callback=None, global_args=True):
        if self.busy:
            messagebox.showinfo('Busy','Wait for the current operation or click Stop.'); return
        self.aws = find_aws()
        if not self.aws: self.initial(); return
        profile = self.profile.get().strip()
        if not profile: messagebox.showerror('Profile','Enter a profile name.'); return
        cmd = [self.aws] + args
        if global_args:
            cmd += ['--profile',profile,'--output','json','--no-cli-pager','--no-cli-auto-prompt']
            if self.region.get().strip(): cmd += ['--region',self.region.get().strip()]
        self.busy = True; self.cancelled.clear(); self.progress.start(); self.status.set('Running: ' + ' '.join(args[:2]))
        self.write('\nRunning ' + ' '.join(args[:2]) + ' | profile: ' + profile + '\n')
        def worker():
            lines = []; total = 0
            try:
                self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                    text=True, encoding='utf-8', errors='replace', env=aws_env(), creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if self.cancelled.is_set(): self.proc.terminate()
                for line in self.proc.stdout:
                    if callback:
                        total += len(line)
                        if total > 16_000_000: raise ValueError('Response exceeds 16 MB. Narrow your query or use the command console.')
                        lines.append(line)
                    self.q.put(('text',line))
                rc = self.proc.wait()
                self.q.put(('text',f'\nExit code: {rc}' + (' (cancelled; completed changes are not rolled back)' if self.cancelled.is_set() else '') + '\n'))
                if rc == 0 and callback and not self.cancelled.is_set(): self.q.put(('callback',(callback,''.join(lines))))
            except Exception as exc:
                if self.proc and self.proc.poll() is None: self.proc.terminate(); self.proc.wait()
                self.q.put(('text',f'Error: {exc}\n'))
            finally: self.proc = None; self.q.put(('done',None))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        for _ in range(250):
            try: kind, data = self.q.get_nowait()
            except queue.Empty: break
            if kind == 'text': self.write(data)
            elif kind == 'done': self.busy=False; self.progress.stop(); self.status.set('Ready — see exit code above')
            elif kind == 'callback':
                try: data[0](data[1])
                except Exception as exc: self.write(f'Response parsing error: {exc}\n')
        self.after(80,self.poll)

    def refresh_profiles(self):
        self.run(['configure','list-profiles'], lambda text: self.profiles.configure(values=text.splitlines()), False)

    def show_identity(self, text):
        obj=json.loads(text); self.identity.set(f"Account: {obj['Account']}   |   {obj['Arn']}")

    def setup(self):
        win=tk.Toplevel(self); win.title('Profiles and sign-in'); win.geometry('490x300')
        ttk.Label(win,text='Profile name (new or existing)').pack(pady=10)
        name=tk.StringVar(value=self.profile.get()); ttk.Entry(win,textvariable=name,width=40).pack()
        def launch(args):
            self.aws=find_aws()
            profile=name.get().strip()
            if not self.aws: self.install_cli(); return
            if not profile or not re.fullmatch(r'[A-Za-z0-9_.@-]+',profile):
                messagebox.showerror('Profile','Use letters, numbers, _, -, . or @.'); return
            try:
                subprocess.Popen([self.aws]+args+['--profile',profile], env=aws_env(), creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0))
                self.profile.set(profile)
                messagebox.showinfo('Setup','Complete the prompts in the new console, then click Refresh and Verify account.')
            except OSError as exc: messagebox.showerror('Setup',str(exc))
        for label,args in [('Configure access keys',['configure']),('Configure SSO',['configure','sso']),('SSO login',['sso','login']),('Console-based login (recent CLI)',['login'])]:
            ttk.Button(win,text=label,command=lambda a=args:launch(a)).pack(fill='x',padx=30,pady=3)
        ttk.Label(win,text='Credentials remain in AWS CLI storage, not application settings.').pack(pady=8)

    def s3_uri(self):
        bucket=self.bucket.get().strip()
        if bucket.startswith('arn:aws:s3:::'): bucket=bucket[13:]
        if bucket.startswith('s3://'): bucket=bucket[5:].rstrip('/')
        if not bucket or '/' in bucket or any(c.isspace() for c in bucket): raise ValueError('Enter a bucket name, without folders.')
        return bucket, 's3://' + bucket + '/' + self.prefix.get().lstrip('/')

    def list_buckets(self):
        self.run(['s3api','list-buckets'],lambda t:self.buckets.configure(values=[b['Name'] for b in json.loads(t).get('Buckets',[])]))

    def browse(self, next_page=False):
        try: bucket,_=self.s3_uri()
        except ValueError as exc: messagebox.showerror('Bucket',str(exc)); return
        context=(self.profile.get(),self.region.get(),bucket,self.prefix.get())
        if next_page and (not self.token or getattr(self,'page_context',None)!=context):
            messagebox.showinfo('Browse','No next page. Click Browse to start.'); return
        args=['s3api','list-objects-v2','--bucket',bucket,'--prefix',self.prefix.get(),'--max-keys','1000','--no-paginate']
        if next_page: args += ['--continuation-token',self.token]
        def display(text):
            obj=json.loads(text); self.token=obj.get('NextContinuationToken'); self.page_context=context
            self.tree.delete(*self.tree.get_children())
            for item in obj.get('Contents',[]): self.tree.insert('', 'end',values=(item['Key'],item['Size'],item.get('LastModified','')))
        self.run(args,display)

    def choose_folder(self):
        value=filedialog.askdirectory()
        if value: self.destination.set(value)

    def sync(self, dry=False):
        try: _,uri=self.s3_uri()
        except ValueError as exc: messagebox.showerror('Bucket',str(exc)); return
        destination=self.destination.get().strip()
        if not destination: messagebox.showerror('Folder','Choose a local destination.'); return
        if not dry and not messagebox.askyesno('Download',f'Download {uri}\nto {destination}?\nExisting local files may be overwritten.'): return
        args=['s3','sync',uri,destination,'--no-progress']
        if dry: args.append('--dryrun')
        self.run(args)

    def selected(self):
        items=self.tree.selection()
        if not items: raise ValueError('Select an object first.')
        bucket,_=self.s3_uri()
        context=(self.profile.get(),self.region.get(),bucket,self.prefix.get())
        if getattr(self,'page_context',None)!=context: raise ValueError('Profile or bucket changed. Browse again before selecting an object.')
        return bucket,self.tree.item(items[0],'values')[0]

    def download_selected(self):
        try: bucket,key=self.selected()
        except ValueError as exc: messagebox.showerror('Selection',str(exc)); return
        if key.endswith('/'): messagebox.showinfo('Folder marker','Use Download bucket / prefix for folders.'); return
        target=filedialog.asksaveasfilename(initialfile=key.rsplit('/',1)[-1])
        if target: self.run(['s3','cp','s3://'+bucket+'/'+key,target,'--no-progress'])

    def upload(self):
        try: _,uri=self.s3_uri()
        except ValueError as exc: messagebox.showerror('Bucket',str(exc)); return
        source=filedialog.askopenfilename()
        if not source: return
        target=uri.rstrip('/')+'/'+Path(source).name
        if messagebox.askyesno('Upload',f'Upload {source}\nto {target}?\nAn existing object with this key may be overwritten.'):
            self.run(['s3','cp',source,target,'--no-progress'])

    def delete(self):
        try: bucket,key=self.selected()
        except ValueError as exc: messagebox.showerror('Selection',str(exc)); return
        if simpledialog.askstring('Delete object',f'Delete s3://{bucket}/{key}?\nType DELETE to confirm:')=='DELETE':
            self.run(['s3api','delete-object','--bucket',bucket,'--key',key])

    def custom(self):
        try: args=parse_command(self.command.get())
        except ValueError as exc: messagebox.showerror('Command',str(exc)); return
        if args[0] in ('configure','login','logout') or args[:2]==['sso','login']:
            messagebox.showinfo('Interactive command','Use Setup / Login for interactive configuration.'); return
        if any(a.split('=')[0] in ('--profile','--region','--output','--debug','--cli-auto-prompt') for a in args):
            messagebox.showerror('Options','Use the profile, region and format controls. Debug and auto-prompt are disabled here.'); return
        if messagebox.askyesno('Run AWS command',f'Profile: {self.profile.get()}\nRegion: {self.region.get()}\n\n{self.command.get()}\n\nThis command may change AWS resources or incur charges. Run?'):
            # run() appends JSON, so pass custom format through a dedicated final option adjustment.
            self.run_custom(args)

    def run_custom(self,args):
        args=args+['--profile',self.profile.get(),'--output',self.output_format.get(),'--no-cli-pager','--no-cli-auto-prompt']
        if self.region.get().strip(): args += ['--region',self.region.get().strip()]
        self.run(args,global_args=False)

    def export(self):
        path=filedialog.asksaveasfilename(defaultextension='.txt',initialfile='aws-output.txt')
        if path:
            try: Path(path).write_text(self.log.get('1.0','end'),encoding='utf-8')
            except OSError as exc: messagebox.showerror('Export',str(exc))

    def stop(self):
        self.cancelled.set()
        if self.proc and self.proc.poll() is None:
            try: self.proc.terminate()
            except OSError: pass

    def close(self):
        if self.busy and not messagebox.askyesno('Exit','An operation is running. Stop and exit? Completed changes cannot be undone.'): return
        self.stop(); self.destroy()

if __name__=='__main__':
    from explorer import ExplorerApp
    ExplorerApp().mainloop()
