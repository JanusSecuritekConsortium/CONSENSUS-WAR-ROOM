"""Local secret entry for the existing Msty Go MCP endpoint."""
import json
import threading
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlsplit
from . import store
from .msty_local import Client


def main():
    root=tk.Tk()
    root.title('Aurelius — conexión local para audio')
    root.geometry('650x310')
    frame=ttk.Frame(root,padding=18);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Copia estos datos desde Msty Go → Settings → Tools.\nEl token se guarda cifrado en este PC; no lo envíes por chat.',wraplength=600).pack(anchor='w',pady=(0,12))
    ttk.Label(frame,text='URL del endpoint MCP local').pack(anchor='w')
    url=tk.StringVar(value='http://127.0.0.1:6274/mcp');ttk.Entry(frame,textvariable=url,width=80).pack(fill='x',pady=(0,8))
    ttk.Label(frame,text='Token de autorización (con o sin «Bearer»)').pack(anchor='w')
    token=tk.StringVar();ttk.Entry(frame,textvariable=token,show='•',width=80).pack(fill='x')
    state=tk.StringVar(value='Solo se comprueba la conexión; no se envían mensajes ni se cambia la agenda.')
    def check():
        address=url.get().strip();secret=token.get().strip()
        if secret.lower().startswith('bearer '):secret=secret[7:].strip()
        parsed=urlsplit(address)
        if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.username or parsed.password or parsed.query or parsed.fragment or not secret:
            state.set('Introduce una URL HTTP local y su token.');return
        button.config(state='disabled');state.set('Comprobando conexión…')
        def worker():
            client=Client({'url':address,'token':secret})
            try:
                client.initialize();tools=client.tools()
                store.secret_write('msty-local-mcp',{'url':address,'token':secret})
                store.ROOT.mkdir(parents=True,exist_ok=True)
                (store.ROOT/'msty-local-tools.json').write_text(json.dumps(tools,ensure_ascii=False,indent=2),encoding='utf-8')
                root.after(0,lambda:state.set('Conexión verificada y guardada. Puedes cerrar esta ventana.'))
            except Exception:
                root.after(0,lambda:state.set('No se pudo conectar. Comprueba que Msty Go está abierto y los datos son correctos.'))
            finally:
                client.close();root.after(0,lambda:button.config(state='normal'))
        threading.Thread(target=worker,daemon=True).start()
    button=ttk.Button(frame,text='Comprobar y guardar',command=check);button.pack(anchor='w',pady=14)
    ttk.Label(frame,textvariable=state,wraplength=600).pack(anchor='w')
    root.mainloop()


if __name__=='__main__':main()
