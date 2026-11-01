"""Bounded background S3 image downloads and Tk image preview."""
import io
import queue
import subprocess
import tempfile
import threading
from pathlib import Path
from collections import OrderedDict
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageOps
from aws_manager import find_aws, aws_env
from file_views import is_picture

MAX_BYTES=32*1024*1024
Image.MAX_IMAGE_PIXELS=40_000_000

def decode_image(data):
    if len(data)>MAX_BYTES:raise ValueError('Image exceeds the 32 MB preview limit.')
    with Image.open(io.BytesIO(data)) as img:
        if img.width*img.height>40_000_000:raise ValueError('Image exceeds the 40 megapixel preview limit.')
        return ImageOps.exif_transpose(img).convert('RGBA')

class Pictures:
    def __init__(self,app):
        self.app=app;self.cache=OrderedDict();self.pending=set();self.failed={};self.requests=queue.Queue(maxsize=96);self.results=queue.Queue();self.closed=threading.Event();self.procs=set();self.lock=threading.Lock();self.waiting=None;self.preview=None
        for _ in range(2):threading.Thread(target=self.worker,daemon=True).start()
        app.after(120,self.poll)
    def token(self,ident):
        item=self.app.rows[ident];ctx=self.app.context()
        return (ctx[0],ctx[1],ctx[2],item['key'],item.get('modified',''),item['size'])
    def request(self,ident,preview=False):
        try:
            item=self.app.rows[ident];key=self.token(ident)
            if self.app.context()!=getattr(self.app,'page_context',None):return None
        except (KeyError,ValueError):return None
        if not is_picture(item['key']):return None
        if preview:self.waiting=key
        if key in self.cache:
            self.cache.move_to_end(key)
            if preview:self.show(key)
            return self.cache[key][0]
        if item['size']>MAX_BYTES:
            if preview:messagebox.showinfo('Image preview','Images up to 32 MB are supported. Download this file to view it locally.')
            self.waiting=None if preview else self.waiting;return None
        if key in self.failed:
            if preview:messagebox.showerror('Image preview',self.failed[key]);self.waiting=None
            return None
        if key not in self.pending:
            try:self.requests.put_nowait(key);self.pending.add(key)
            except queue.Full:pass
        if preview:self.app.status.set('Loading image preview…')
        return None
    def worker(self):
        while not self.closed.is_set():
            try:key=self.requests.get(timeout=.25)
            except queue.Empty:continue
            proc=None
            try:
                aws=find_aws()
                if not aws:raise RuntimeError('AWS CLI not found.')
                with tempfile.TemporaryDirectory(prefix='aws-picture-') as folder:
                    path=Path(folder)/'image'
                    args=[aws,'s3api','get-object','--bucket',key[2],'--key',key[3],'--range',f'bytes=0-{MAX_BYTES}','--profile',key[0],'--no-cli-pager','--no-cli-auto-prompt',str(path)]
                    if key[1]:args+=['--region',key[1]]
                    proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=aws_env(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    with self.lock:self.procs.add(proc)
                    out,err=proc.communicate(timeout=90)
                    if proc.returncode:raise RuntimeError(err.decode('utf-8','replace')[:1200] or 'Image download failed.')
                    data=path.read_bytes();img=decode_image(data);img.thumbnail((200,200),Image.Resampling.LANCZOS)
                    self.results.put((key,(img,data),None))
            except Exception as exc:
                if proc and proc.poll() is None:proc.kill();proc.communicate()
                self.results.put((key,None,str(exc)))
            finally:
                if proc:
                    with self.lock:self.procs.discard(proc)
    def poll(self):
        if self.closed.is_set():return
        changed=False
        for _ in range(8):
            try:key,value,error=self.results.get_nowait()
            except queue.Empty:break
            self.pending.discard(key)
            if error:self.failed[key]=error
            else:
                self.cache[key]=value;self.cache.move_to_end(key)
                while len(self.cache)>80 or sum(len(v[1]) for v in self.cache.values())>96*1024*1024:self.cache.popitem(last=False)
                changed=True
            if self.waiting==key:
                self.waiting=None
                if error:messagebox.showerror('Image preview',error)
                else:self.show(key)
        if changed:self.app.tree.schedule()
        self.app.after(120,self.poll)
    def show(self,key):
        self.waiting=None
        if key not in self.cache:return
        try:img=decode_image(self.cache[key][1])
        except Exception as exc:messagebox.showerror('Image preview',str(exc));return
        if self.preview and self.preview.winfo_exists():self.preview.destroy()
        self.preview=Preview(self.app,img,key[3]);self.app.status.set('Image preview ready')
    def close(self):
        self.closed.set()
        with self.lock:
            for proc in self.procs:
                if proc.poll() is None:proc.terminate()

class Preview(tk.Toplevel):
    def __init__(self,app,img,name):
        super().__init__(app);self.original=img;self.img=img;self.scale=1.;self.fit_mode=True;self.photo=None
        self.title('Image preview — '+name);self.geometry('1000x740');self.minsize(620,420)
        tools=ttk.Frame(self,padding=8);tools.pack(fill='x')
        for title,fn in [('Fit',self.fit),('100%',lambda:self.zoom(1,True)),('−',lambda:self.zoom(.8)),('+',lambda:self.zoom(1.25)),('Rotate left',lambda:self.rotate(90)),('Rotate right',lambda:self.rotate(-90)),('Save PNG copy',self.save),('Close',self.destroy)]:ttk.Button(tools,text=title,command=fn).pack(side='left',padx=2)
        frame=ttk.Frame(self);frame.pack(fill='both',expand=True);frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(frame,bg='#1b2634',highlightthickness=0);self.canvas.grid(row=0,column=0,sticky='nsew')
        x=ttk.Scrollbar(frame,orient='horizontal',command=self.canvas.xview);x.grid(row=1,column=0,sticky='ew');y=ttk.Scrollbar(frame,command=self.canvas.yview);y.grid(row=0,column=1,sticky='ns');self.canvas.configure(xscrollcommand=x.set,yscrollcommand=y.set)
        self.info=tk.StringVar();ttk.Label(self,textvariable=self.info,padding=8).pack(fill='x')
        self.canvas.bind('<Configure>',lambda e:self.fit() if self.fit_mode else self.draw())
        self.canvas.bind('<MouseWheel>',lambda e:self.zoom(1.15 if e.delta>0 else 1/1.15))
        self.canvas.bind('<ButtonPress-1>',lambda e:self.canvas.scan_mark(e.x,e.y));self.canvas.bind('<B1-Motion>',lambda e:self.canvas.scan_dragto(e.x,e.y,gain=1))
        self.bind('<Escape>',lambda _:self.destroy());self.after(50,self.fit)
    def fit(self):
        self.fit_mode=True;self.scale=min(max(1,self.canvas.winfo_width())/self.img.width,max(1,self.canvas.winfo_height())/self.img.height,1);self.draw();self.canvas.xview_moveto(0);self.canvas.yview_moveto(0)
    def zoom(self,value,absolute=False):self.fit_mode=False;self.scale=max(.02,min(8,value if absolute else self.scale*value));self.draw()
    def rotate(self,angle):self.img=self.img.rotate(angle,expand=True);self.fit()
    def draw(self):
        # Bound rendered bitmap memory even for huge originals or high zoom.
        scale=min(self.scale,8192/max(self.img.size),(24_000_000/(self.img.width*self.img.height))**.5);self.scale=scale
        w=max(1,int(self.img.width*scale));h=max(1,int(self.img.height*scale));display=self.img.resize((w,h),Image.Resampling.LANCZOS)
        self.photo=ImageTk.PhotoImage(display,master=self);c=self.canvas;c.delete('all');cw=max(w,c.winfo_width());ch=max(h,c.winfo_height());c.create_image(cw/2,ch/2,image=self.photo);c.configure(scrollregion=(0,0,cw,ch));self.info.set(f'{self.img.width} × {self.img.height} pixels  |  {scale:.0%}  |  Mouse wheel: zoom • Drag: pan • Esc: close • Rotation affects preview/local copy only')
    def save(self):
        name=filedialog.asksaveasfilename(parent=self,defaultextension='.png',filetypes=[('PNG image','*.png')])
        if name:
            try:self.img.save(name,'PNG')
            except OSError as exc:messagebox.showerror('Save',str(exc),parent=self)
