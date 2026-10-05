"""Interactive account setup. Secrets are entered locally, never through chat."""
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from . import store
from .connectors import collect, microsoft_app, save_microsoft_cache, SCOPES
from .status import account_status, account_label, missing_fields


def main():
    config = store.load()
    root = tk.Tk()
    root.title('Aurelius — Local account integrations')
    root.geometry('1250x850')
    tk.Label(root, text='Local Msty integrations — read-only mail, calendar and Drive', font=('Segoe UI', 15)).pack(pady=12)
    tk.Label(root, text='Secrets are encrypted for this Windows user. No SMTP, cloud AI, or automatic replies.').pack()
    frame = ttk.Frame(root)
    frame.pack(fill='both', expand=True, padx=15, pady=10)
    selector = tk.Listbox(frame, width=60, exportselection=False)
    selector.pack(side='left', fill='y')
    right = ttk.Frame(frame)
    right.pack(side='left', fill='both', expand=True, padx=18)
    for account in config['accounts']:
        selector.insert('end', account_label(account))
    fields = {}
    selected = [None]
    feedback = tk.StringVar(value='Select an account. Save, then Test connection.')
    enabled = tk.BooleanVar()
    verified = set()
    status_text = tk.StringVar()

    def refresh_status():
        current = selector.curselection()
        selector.delete(0, 'end')
        for account in config['accounts']:
            selector.insert('end', account_label(account))
        if current:
            selector.selection_set(current[0])
        if selected[0] is not None:
            status_text.set(account_status(selected[0]))

    def dirty():
        account = selected[0]
        return account is not None and (enabled.get() != account.get('enabled', False)
            or any(entry.get() != ('' if key == 'secret' else str(account.get(key, '')))
                   for key, entry in fields.items()))

    def confirm_changes():
        if not dirty():
            return True
        answer = messagebox.askyesnocancel('Unsaved account changes',
            'Save changes to ' + selected[0]['label'] + '?\nYes: save. No: discard. Cancel: keep editing.', parent=root)
        return save() if answer is True else answer is False
    explanations = {
        'bridge': 'Use the username/password and port shown inside Proton Mail Bridge, not your Proton login password. Start Bridge and export its TLS certificate; select only the certificate PEM as ca_file. Host must stay loopback. Default STARTTLS port is editable.',
        'gmail': 'Use the full Google account address and an app password from Google Account → Security → App passwords. Google Workspace may require admin approval. The normal account password will not work. Sent folder is discovered automatically, or enter its exact IMAP name.',
        'icloud': 'Apple iCloud Mail: use your iCloud Mail username (or full email address) and an app-specific password from account.apple.com → Sign-In and Security → App-Specific Passwords. Your regular Apple Account password will not work here. Server: imap.mail.me.com, SSL, port 993. Inbox and Sent are read only.',
        'imap': 'Use your full mailbox address and mailbox password. SSL/TLS is required. Sent folder is discovered automatically; provide its exact name if the test reports it missing.',
        'outlook': 'Use the exact Outlook account address and your Microsoft Entra application (client) ID. Register a public-client app supporting personal Microsoft accounts, allow public-client/device-code flows, and add delegated Microsoft Graph Mail.Read and User.Read. Save, then Microsoft sign-in. No client secret is needed.',
        'calendar': 'For named appointments choose Full view in Proton Calendar > Settings > All settings > Calendars > Share with anyone > Create link. Enter that HTTPS link in Secret and clear path. Limited view only returns Busy blocks. Alternatively select a local .ics export with titles (refresh it manually). Anyone with the link can read its details; it is encrypted locally. Shared feeds may lag up to 8 hours.',
        'drive': 'Select the local Proton Drive sync folder. The connector lists recently changed filenames only. It does not read documents, upload files, or force cloud-only files to download.',
    }

    def render(_=None):
        if not selector.curselection():
            return
        account = config['accounts'][selector.curselection()[0]]
        if account is selected[0]:
            return
        if not confirm_changes():
            selector.selection_clear(0, 'end')
            selector.selection_set(config['accounts'].index(selected[0]))
            return
        selected[0] = account
        for child in right.winfo_children():
            child.destroy()
        fields.clear()
        ttk.Label(right, text=account['label'], font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        status_text.set(account_status(account))
        ttk.Label(right, textvariable=status_text, wraplength=590).pack(anchor='w', pady=5)
        ttk.Label(right, text=explanations[account['kind']], wraplength=590).pack(anchor='w', pady=12)
        names = ['username', 'host', 'port', 'tls', 'sent_folder', 'ca_file'] if account['kind'] in ('imap', 'gmail', 'icloud', 'bridge') else (['username', 'client_id'] if account['kind']=='outlook' else ['path'])
        for key in names:
            if key not in account:
                continue
            ttk.Label(right, text=key.replace('_', ' ')).pack(anchor='w')
            entry = ttk.Entry(right, width=75)
            entry.insert(0, str(account.get(key, '')))
            entry.pack(anchor='w', pady=(0, 5))
            fields[key] = entry
        if account['kind'] in ('calendar', 'drive', 'bridge'):
            def browse():
                path = filedialog.askdirectory() if account['kind']=='drive' else filedialog.askopenfilename()
                key = 'ca_file' if account['kind']=='bridge' else 'path'
                if path:
                    fields[key].delete(0, 'end')
                    fields[key].insert(0, path)
            ttk.Button(right, text='Choose local file/folder', command=browse).pack(anchor='w', pady=4)
        if account['kind'] not in ('outlook', 'drive'):
            ttk.Label(right, text='Secret: password/app password/Bridge password, or calendar URL (blank keeps saved value)').pack(anchor='w')
            entry = ttk.Entry(right, show='*', width=75)
            entry.pack(anchor='w', pady=5)
            fields['secret'] = entry
        enabled.set(account.get('enabled', False))
        ttk.Checkbutton(right, text='Include this source in local reviews', variable=enabled).pack(anchor='w', pady=6)

    def save():
        account = selected[0]
        if account is None:
            return False
        try:
            update = {key: entry.get().strip() for key, entry in fields.items() if key != 'secret'}
            if 'port' in update:
                update['port'] = int(update['port'])
                if not 1 <= update['port'] <= 65535 or update.get('tls') not in ('ssl', 'starttls'):
                    raise ValueError()
            if account['kind']=='bridge' and update.get('host') not in ('127.0.0.1', 'localhost', '::1'):
                raise ValueError()
            changed = any(account.get(key)!=value for key,value in update.items()) or bool(
                'secret' in fields and fields['secret'].get())
            if 'secret' in fields and fields['secret'].get():
                verified.discard(account['id'])
                secret = store.secret_read(account['id'])
                secret['url' if account['kind']=='calendar' else 'password'] = fields['secret'].get()
                store.secret_write(account['id'], secret)
                fields['secret'].delete(0, 'end')
            if any(account.get(key)!=value for key,value in update.items()):
                verified.discard(account['id'])
            account.update(update, enabled=enabled.get())
            account['setup_saved'] = True
            if changed:
                account.pop('last_test_at', None)
                account.pop('last_test_ok', None)
                account.pop('last_test_warnings', None)
            store.save(config)
            refresh_status()
            feedback.set('Saved locally. Test the source before relying on its data.')
            return True
        except Exception:
            feedback.set('Could not save. Check fields, port, TLS and local file access.')
            return False

    def test():
        if not save():
            return
        missing = missing_fields(selected[0])
        if missing:
            feedback.set('Setup incomplete. Missing: ' + ', '.join(missing))
            return
        account = dict(selected[0], enabled=True)
        original = dict(selected[0])
        feedback.set('Testing read-only connection…')
        def worker():
            result = collect({'accounts': [account]})[0]
            message = result['status']
            if result['status']=='ok':
                message += ': '+', '.join(str(len(result[key]))+' '+key for key in ('messages','events','files') if key in result)
                message += '\n'+'; '.join(result.get('warnings', []))
            else:
                message += ' ('+result.get('error_type', 'setup required')+'). Check credentials and settings.'
            def finish():
                target = next(a for a in config['accounts'] if a['id'] == account['id'])
                if target != original:
                    feedback.set(account['label'] + ': settings changed during the test; test again.')
                    return
                if result['status'] == 'ok':
                    verified.add(account['id'])
                else:
                    verified.discard(account['id'])
                target['last_test_at'] = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')
                target['last_test_ok'] = result['status'] == 'ok'
                target['last_test_warnings'] = result.get('warnings', [])
                try:
                    store.save(config)
                    refresh_status()
                    feedback.set(account['label'] + ': ' + message)
                except Exception:
                    feedback.set(account['label'] + ': test finished, but its status could not be saved.')
            root.after(0, finish)
        threading.Thread(target=worker, daemon=True).start()

    def activate():
        # A calendar and a mailbox must have passed tests in this setup session.
        active = [a for a in config['accounts'] if a.get('enabled')]
        if not any(a['kind']=='calendar' and a['id'] in verified for a in active) or not any(a['kind'] in ('imap','gmail','icloud','bridge','outlook') and a['id'] in verified for a in active):
            feedback.set('First enable and successfully test at least one calendar and one mailbox in this window.')
            return
        try:
            from .schedules import install
            install(enable=True)
            feedback.set('Msty reviews enabled: daily 07:15, weekdays 17:35, Sunday 18:00, Europe/Madrid. Results stay in Msty.')
        except Exception:
            feedback.set('Could not enable Msty schedules. Existing reports were preserved.')

    def microsoft_login():
        if not save() or selected[0]['kind']!='outlook':
            return
        if not selected[0].get('username') or not selected[0].get('client_id'):
            feedback.set('Microsoft sign-in needs your Outlook address and application client ID first.')
            return
        account = dict(selected[0])
        def worker():
            try:
                app, cache = microsoft_app(account)
                flow = app.initiate_device_flow(scopes=SCOPES)
                if 'user_code' not in flow:
                    raise ValueError()
                instruction = 'Open '+flow['verification_uri']+' and enter '+flow['user_code']+'\nSign in as '+account['username']
                root.after(0, lambda: feedback.set(instruction))
                result = app.acquire_token_by_device_flow(flow)
                if 'access_token' not in result or not app.get_accounts(username=account['username']):
                    raise ValueError()
                save_microsoft_cache(account, cache)
                def signed_in():
                    verified.discard(account['id'])
                    target = next(a for a in config['accounts'] if a['id'] == account['id'])
                    target.pop('last_test_at', None)
                    target.pop('last_test_ok', None)
                    target.pop('last_test_warnings', None)
                    store.save(config)
                    refresh_status()
                    feedback.set(account['label'] + ': Microsoft sign-in saved securely. You can now Test connection.')
                root.after(0, signed_in)
            except Exception:
                root.after(0, lambda: feedback.set('Microsoft sign-in failed. Check client ID, public-client settings and account address.'))
        threading.Thread(target=worker, daemon=True).start()

    bar = ttk.Frame(root)
    bar.pack(fill='x', padx=20)
    ttk.Button(bar, text='Save locally', command=save).pack(side='left', padx=5)
    ttk.Button(bar, text='Test connection', command=test).pack(side='left', padx=5)
    ttk.Button(bar, text='Microsoft sign-in', command=microsoft_login).pack(side='left', padx=5)
    ttk.Button(bar, text='Enable Msty review schedules', command=activate).pack(side='left', padx=5)
    ttk.Label(root, textvariable=feedback, wraplength=920).pack(fill='x', padx=20, pady=20)
    selector.bind('<<ListboxSelect>>', render)
    selector.selection_set(0)
    render()
    def close():
        if confirm_changes():
            root.destroy()
    root.protocol('WM_DELETE_WINDOW', close)
    root.mainloop()


if __name__ == '__main__':
    main()
