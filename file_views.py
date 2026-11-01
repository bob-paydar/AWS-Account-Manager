"""Virtualized file views sharing the existing selection API."""
import math
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk

VIEWS=('Extra large icons','Large icons','Medium icons','Small icons','List','Details','Tiles')
IMAGE_EXTS={'.png','.jpg','.jpeg','.gif','.webp','.bmp','.tif','.tiff','.ico'}
def is_picture(key):
    from pathlib import PurePosixPath
    return PurePosixPath(key).suffix.lower() in IMAGE_EXTS

def layout(mode,width):
    if mode=='Details': return max(width,650),46,32,1
    if mode=='List':return max(width,320),38,26,1
    if mode=='Tiles':return 320,92,64,max(1,width//320)
    size={'Extra large icons':160,'Large icons':112,'Medium icons':72,'Small icons':36}[mode]
    cell=size+54
    return cell,size+65,size,max(1,width//cell)

class FileView(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent);self.app=app;self.records={};self.selected=[];self.images={};self.anchor=None;self.coords={}
        self.header=ttk.Frame(self);self.header.pack(fill='x')
        for col,label in [('name','Name'),('kind','Type'),('size','Bytes'),('modified','Modified')]:
            ttk.Button(self.header,text=label,command=lambda c=col:app.sort_rows(c)).pack(side='left',expand=True,fill='x')
        self.canvas=tk.Canvas(self,bg='#edf3f9',highlightthickness=0,takefocus=True)
        bar=ttk.Scrollbar(self,command=self.scroll);self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda _:self.redraw())
        self.canvas.bind('<MouseWheel>',self.wheel);self.canvas.bind('<Button-4>',lambda _:self.scroll(-3,'units',wheel=True));self.canvas.bind('<Button-5>',lambda _:self.scroll(3,'units',wheel=True))
        self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<Double-1>',self.open_item)
        self.canvas.bind('<Return>',self.open_item)
        self.canvas.bind('<space>',lambda _:app.check_highlight())
        self.canvas.bind('<Control-a>',lambda _:app.selection_action('all'))
        self.canvas.bind('<Button-3>',self.context)
        for key in ('Left','Right','Up','Down'):self.canvas.bind('<'+key+'>',lambda e,k=key:self.arrow(k,e))
        self.mode='Large icons';self.pending=None
    def schedule(self):
        if self.pending is None:self.pending=self.after_idle(self.redraw)
    def get_children(self):return tuple(self.records)
    def delete(self,*ids):
        for ident in ids:self.records.pop(ident,None)
        self.selected=[i for i in self.selected if i in self.records];self.schedule()
    def insert(self,parent,index,iid=None,values=()):self.records[iid]=values;self.schedule();return iid
    def exists(self,ident):return ident in self.records
    def selection(self):return tuple(self.selected)
    def selection_set(self,ids):
        if isinstance(ids,str):ids=[ids]
        self.selected=[i for i in ids if i in self.records];self.schedule()
    def selection_remove(self,*ids):self.selected=[i for i in self.selected if i not in ids];self.schedule()
    def item(self,ident,option=None):return self.records[ident] if option=='values' else {'values':self.records[ident]}
    def identify_row(self,y):
        real=self.canvas.canvasy(y)
        for ident,(x0,y0,x1,y1) in self.coords.items():
            if y0<=real<y1 and x0<=getattr(self,'last_x',0)<x1:return ident
        return ''
    def identify_column(self,x):return '#1' if getattr(self,'on_check',False) else '#2'
    def hit(self,event):
        self.last_x=self.canvas.canvasx(event.x); ident=self.identify_row(event.y)
        self.on_check=bool(ident and self.last_x<self.coords[ident][0]+27 and self.canvas.canvasy(event.y)<self.coords[ident][1]+29)
        return ident
    def click(self,event):
        self.canvas.focus_set();ident=self.hit(event)
        if not ident:return
        if self.on_check:
            self.app.checked.symmetric_difference_update({ident});self.app.render();return 'break'
        ids=list(self.records)
        if event.state&1 and self.anchor in ids:
            a,b=sorted((ids.index(self.anchor),ids.index(ident)));self.selection_set(ids[a:b+1])
        elif event.state&4:
            self.selection_set([i for i in self.selected if i!=ident] if ident in self.selected else self.selected+[ident]);self.anchor=ident
        else:self.selection_set([ident]);self.anchor=ident
        # Plain single click opens pictures; modified click remains selection-only.
        if not event.state&5 and is_picture(self.app.rows[ident]['key']):self.app.preview_picture(ident)
    def open_item(self,event=None):
        if event and getattr(event,'num',None)==1:
            ident=self.hit(event)
            if not ident or self.on_check:return 'break'
            self.selection_set([ident])
        self.app.activate();return 'break'
    def context(self,event):self.hit(event);self.app.context_menu(event)
    def arrow(self,key,event):
        ids=list(self.records)
        if not ids:return 'break'
        _,_,_,cols=layout(self.mode,max(1,self.canvas.winfo_width()))
        pos=ids.index(self.selected[-1]) if self.selected else 0
        pos=max(0,min(len(ids)-1,pos+{'Left':-1,'Right':1,'Up':-cols,'Down':cols}[key]))
        self.selection_set([ids[pos]]);_,h,_,_=layout(self.mode,max(1,self.canvas.winfo_width()))
        total=max(h,math.ceil(len(ids)/cols)*h);self.canvas.yview_moveto((pos//cols*h)/total);self.redraw();return 'break'
    def wheel(self,event):self.scroll(-int(event.delta/120) if abs(event.delta)>=120 else (-1 if event.delta>0 else 1),'units',wheel=True);return 'break'
    def scroll(self,*args,wheel=False):
        if wheel:self.canvas.yview_scroll(*args)
        else:self.canvas.yview(*args)
        self.redraw()
    def redraw(self):
        if self.pending is not None:
            self.after_cancel(self.pending);self.pending=None
        if not self.winfo_exists():return
        self.mode=self.app.view_mode.get()
        if self.mode=='Details':self.header.pack(fill='x',before=self.canvas)
        else:self.header.pack_forget()
        c=self.canvas;c.delete('all');self.images.clear();self.coords.clear()
        width=max(1,c.winfo_width());cw,ch,size,cols=layout(self.mode,width);cw=width/cols if self.mode not in ('Details','List') else width
        total=max(ch,math.ceil(len(self.records)/cols)*ch);c.configure(scrollregion=(0,0,width,total),yscrollincrement=25)
        top=c.canvasy(0);bottom=top+c.winfo_height();start=max(0,int(top//ch)*cols);end=min(len(self.records),(int(bottom//ch)+2)*cols)
        ids=list(self.records)
        for index in range(start,end):
            ident=ids[index];values=self.records[ident];check,name,kind,bytes_,modified=values
            x=(index%cols)*cw;y=(index//cols)*ch;self.coords[ident]=(x,y,x+cw,y+ch)
            selected=ident in self.selected;bg='#cde6ff' if selected else ('#ffffff' if index%2==0 else '#f2f7fc')
            c.create_rectangle(x+3,y+3,x+cw-3,y+ch-3,fill=bg,outline='#4b91d1' if selected else '#d6e2ee')
            c.create_text(x+15,y+16,text=check,fill='#1263a0',font=('Segoe UI',12))
            inline=self.mode in ('Details','List','Tiles');ix=x+34+size/2 if inline else x+cw/2;iy=y+ch/2 if inline else y+28+size/2
            image=self.app.picture_asset(ident,size)
            if image:
                photo=ImageTk.PhotoImage(image,master=self);self.images[ident]=photo;c.create_image(ix,iy,image=photo)
            else:
                color='#e2ae35' if kind=='Folder' else '#438ab7' if is_picture(name) else '#7791aa'
                c.create_rectangle(ix-size*.35,iy-size*.36,ix+size*.35,iy+size*.36,fill=color,outline='')
                label='DIR' if kind=='Folder' else (name.rsplit('.',1)[-1][:5].upper() if '.' in name else 'FILE')
                c.create_text(ix,iy,text=label,fill='white',font=('Segoe UI',max(7,min(12,size//5)),'bold'))
            if inline:
                tx=x+size+45;available=max(40,cw-(size+55))
                if self.mode=='Details':available=max(40,cw*.45-(size+55))
                c.create_text(tx,y+ch/2-(12 if self.mode=='Tiles' else 0),text=name,anchor='w',width=available,fill='#15334c',font=('Segoe UI',10))
                if self.mode=='Tiles':c.create_text(tx,y+ch/2+17,text=f'{kind}  {bytes_} bytes' if kind=='File' else 'Folder',anchor='w',fill='#54718a',font=('Segoe UI',9))
                if self.mode=='Details':
                    for xp,text in ((.48,kind),(.61,str(bytes_)),(.75,str(modified)[:19])):c.create_text(x+cw*xp,y+ch/2,text=text,anchor='w',fill='#49647c',font=('Segoe UI',9))
            else:c.create_text(x+cw/2,y+size+37,text=name,anchor='n',width=max(30,cw-18),fill='#15334c',font=('Segoe UI',10))
