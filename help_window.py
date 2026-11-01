"""Offline searchable help; no account calls or credentials inspected."""
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from pathlib import Path
from help_content import TOPICS, full_guide, search_topics
from aws_manager import find_aws

class HelpWindow(tk.Toplevel):
    def __init__(self,app,topic=0):
        super().__init__(app); self.app=app; self.current=topic; self.visible=[]
        self.title('Help — AWS Account Manager'); self.geometry('1040x720'); self.minsize(720,480)
        self.query=tk.StringVar(); self.fontsize=tk.IntVar(value=11)
        top=ttk.Frame(self,padding=10); top.pack(fill='x')
        ttk.Label(top,text='AWS Setup & Application Help',font=('Segoe UI',16,'bold')).pack(anchor='w')
        row=ttk.Frame(top); row.pack(fill='x',pady=(8,0))
        ttk.Label(row,text='Search help').pack(side='left')
        self.search=ttk.Entry(row,textvariable=self.query); self.search.pack(side='left',fill='x',expand=True,padx=6)
        ttk.Button(row,text='Clear',command=lambda:self.query.set('')).pack(side='left')
        ttk.Label(row,text='Text size').pack(side='left',padx=8)
        ttk.Combobox(row,values=[10,11,12,14,16,18,20],textvariable=self.fontsize,width=4,state='readonly').pack(side='left')
        self.summary=tk.StringVar(); ttk.Label(top,textvariable=self.summary,wraplength=950).pack(anchor='w',pady=(8,0))
        ttk.Button(top,text='Refresh current setup',command=self.refresh_setup).pack(anchor='w')
        panes=ttk.Panedwindow(self,orient='horizontal'); panes.pack(fill='both',expand=True,padx=10)
        left=ttk.Frame(panes); right=ttk.Frame(panes); panes.add(left,weight=1); panes.add(right,weight=4)
        self.topics=tk.Listbox(left,exportselection=False,font=('Segoe UI',10),width=30,activestyle='none')
        scroll=ttk.Scrollbar(left,command=self.topics.yview); self.topics.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); self.topics.pack(fill='both',expand=True)
        self.heading=ttk.Label(right,font=('Segoe UI',14,'bold'),padding=(10,6));self.heading.pack(anchor='w')
        frame=ttk.Frame(right);frame.pack(fill='both',expand=True)
        self.text=tk.Text(frame,wrap='word',padx=16,pady=12,font=('Segoe UI',11),spacing3=5,bg='#fafcff',fg='#172b42',relief='flat')
        y=ttk.Scrollbar(frame,command=self.text.yview);self.text.configure(yscrollcommand=y.set)
        y.pack(side='right',fill='y');self.text.pack(fill='both',expand=True)
        self.text.tag_configure('match',background='#ffe59a');self.text.tag_configure('link',foreground='#1268b3',underline=True)
        self.text.tag_bind('link','<Button-1>',self.open_link)
        self.text.tag_bind('link','<Enter>',lambda _:self.text.configure(cursor='hand2'))
        self.text.tag_bind('link','<Leave>',lambda _:self.text.configure(cursor='xterm'))
        bottom=ttk.Frame(self,padding=10);bottom.pack(fill='x')
        for label,fn in [('Previous',lambda:self.step(-1)),('Next',lambda:self.step(1)),('Copy topic',self.copy_topic),('Save full guide…',self.save_guide)]:ttk.Button(bottom,text=label,command=fn).pack(side='left',padx=3)
        self.position=tk.StringVar();ttk.Label(bottom,textvariable=self.position).pack(side='right')
        self.query.trace_add('write',lambda *_:self.filter_topics())
        self.fontsize.trace_add('write',lambda *_:self.text.configure(font=('Segoe UI',self.fontsize.get())))
        self.topics.bind('<<ListboxSelect>>',self.select_topic)
        self.bind('<Control-f>',lambda e:(self.search.focus_set(),'break')[1])
        self.bind('<Escape>',lambda _:self.destroy())
        self.refresh_setup();self.filter_topics();self.show(topic)

    def refresh_setup(self):
        cli=find_aws()
        self.summary.set('Current setup: '+('AWS CLI found' if cli else 'AWS CLI not found')+' | Profile: '+(self.app.profile.get() or '(none)')+' | Region: '+(self.app.region.get() or '(none)')+' | Bucket: '+(self.app.bucket.get() or '(none)')+'\nLocal settings only; use Verify account in the main window to validate AWS access.')

    def filter_topics(self):
        self.visible=search_topics(self.query.get());self.topics.delete(0,'end')
        for i in self.visible:self.topics.insert('end',TOPICS[i][0])
        if self.visible:self.show(self.current if self.current in self.visible else self.visible[0])
        else:
            self.heading.configure(text='No matching topics');self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('end','Try a shorter search, such as permissions, secret, upload or project.');self.text.configure(state='disabled');self.position.set('0 topics')

    def show(self,index):
        if index not in self.visible:return
        self.current=index;position=self.visible.index(index)
        self.topics.selection_clear(0,'end');self.topics.selection_set(position);self.topics.see(position)
        title,body=TOPICS[index];self.heading.configure(text=title)
        self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('end',body)
        for match in re.finditer(r'https://[^\s]+',body):self.text.tag_add('link',f'1.0+{match.start()}c',f'1.0+{match.end()}c')
        for term in self.query.get().split():
            start='1.0'
            while True:
                found=self.text.search(term,start,stopindex='end',nocase=True)
                if not found:break
                end=f'{found}+{len(term)}c';self.text.tag_add('match',found,end);start=end
        self.text.configure(state='disabled');self.text.yview_moveto(0);self.position.set(f'Topic {position+1} of {len(self.visible)}')

    def select_topic(self,event=None):
        selection=self.topics.curselection()
        if selection:self.show(self.visible[selection[0]])

    def step(self,delta):
        if self.visible:self.show(self.visible[max(0,min(len(self.visible)-1,self.visible.index(self.current)+delta))])

    def copy_topic(self):
        if not self.visible:return
        title,body=TOPICS[self.current];self.clipboard_clear();self.clipboard_append(title+'\n\n'+body)

    def open_link(self,event):
        index=self.text.index(f'@{event.x},{event.y}')
        ranges=self.text.tag_ranges('link')
        for a,b in zip(ranges[::2],ranges[1::2]):
            if self.text.compare(a,'<=',index) and self.text.compare(index,'<',b):webbrowser.open(self.text.get(a,b));break
        return 'break'

    def save_guide(self):
        name=filedialog.asksaveasfilename(parent=self,initialfile='AWS Setup Readme.txt',defaultextension='.txt',filetypes=[('Text file','*.txt')])
        if name:
            try:Path(name).write_text(full_guide(),encoding='utf-8');messagebox.showinfo('Guide saved','The complete guide was saved.',parent=self)
            except OSError as exc:messagebox.showerror('Save guide',str(exc),parent=self)


def install_help(app,menu):
    def show(topic=0):
        window=getattr(app,'help_window',None)
        if window is not None and window.winfo_exists():
            window.query.set('');window.show(topic);window.refresh_setup();window.deiconify();window.lift();window.focus_set()
        else:app.help_window=HelpWindow(app,topic)
    helpmenu=tk.Menu(menu,tearoff=False);menu.add_cascade(label='Help',menu=helpmenu)
    helpmenu.add_command(label='Setup guide and help…',accelerator='F1',command=show)
    helpmenu.add_command(label='Permissions and IAM policy…',command=lambda:show(5))
    helpmenu.add_command(label='Troubleshooting…',command=lambda:show(11))
    helpmenu.add_separator()
    helpmenu.add_command(label='About',command=lambda:messagebox.showinfo('About','AWS Account Manager 1.4\nProgrammer: Bob Paydar\nDesktop AWS CLI manager with offline setup help.'))
    app.bind('<F1>',lambda e:(show(),'break')[1])
