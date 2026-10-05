"""Show fresh, deterministic local briefings without model rewriting."""
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from .service import personal_review


def main():
    root = tk.Tk()
    root.title('Aurelius — Briefing verificado')
    root.geometry('1050x800')
    bar = ttk.Frame(root)
    bar.pack(fill='x',padx=12,pady=10)
    mode = tk.StringVar(value='morning')
    for label,value in [('Próximos siete días','morning'),('Cierre del día','evening'),('Próxima semana','weekly')]:
        ttk.Radiobutton(bar,text=label,variable=mode,value=value).pack(side='left',padx=5)
    state = tk.StringVar(value='Informe directo de las fuentes; no se reescribe con IA.')
    ttk.Label(root,textvariable=state,wraplength=1000).pack(fill='x',padx=12,pady=5)
    body = ScrolledText(root,wrap='word',font=('Segoe UI',10))
    body.pack(fill='both',expand=True,padx=12,pady=10)
    body.configure(state='disabled')
    def finish(text,failed=False):
        body.configure(state='normal')
        body.delete('1.0','end')
        body.insert('1.0',text)
        body.configure(state='disabled')
        state.set('No se pudo completar la consulta.' if failed else 'Consulta terminada. Comprueba la cobertura y la hora del informe.')
        refresh.configure(state='normal')
    def collect():
        selected = mode.get()
        refresh.configure(state='disabled')
        state.set('Consultando las fuentes ahora; puede tardar varios minutos…')
        # Clear the previous report while fetching to avoid showing it as current.
        body.configure(state='normal')
        body.delete('1.0','end')
        body.configure(state='disabled')
        def worker():
            try:
                report = personal_review(selected)['body_text']
                root.after(0,lambda:finish(report))
            except Exception as error:
                kind=type(error).__name__
                root.after(0,lambda:finish('Consulta fallida ('+kind+'). No se reutiliza un informe anterior.',True))
        threading.Thread(target=worker,daemon=True).start()
    refresh=ttk.Button(bar,text='Consultar ahora',command=collect)
    refresh.pack(side='right')
    root.after(200,collect)
    root.mainloop()


if __name__=='__main__':
    main()
