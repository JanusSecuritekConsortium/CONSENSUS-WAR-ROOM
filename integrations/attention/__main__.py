"""Command line for the Personal Attention Manager.

    python -m integrations.attention status | scan | brief [--archive] | list [--kind K] [--state S]
    python -m integrations.attention show ID | done ID | ignore ID | reopen ID | cancel ID | draft ID
    python -m integrations.attention snooze ID UNTIL
    python -m integrations.attention add KIND TITLE [--contact NAME] [--due YYYY-MM-DD] [--due-text TEXT]
    python -m integrations.attention contacts TEXT | link CHANNEL ADDRESS CONTACT_ID [--reject]
    python -m integrations.attention import-contacts [CSV]   (Google Contacts export; starred = favourites)
    python -m integrations.attention pause | resume | export | serve-mcp
"""
from __future__ import annotations

import argparse
import json
import sys

from . import api, export, scan


def show_items(items):
    if not items:
        print('Nothing.')
    for item in items:
        flag = ' (overdue)' if item['overdue'] else ' (to confirm)' if item['review'] else ''
        print(f'{item["id"]:22} {item["priority"]:7} {item["state"].lower():21} {item["title"][:70]}{flag}')


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(prog='python -m integrations.attention', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status')
    commands.add_parser('scan')
    commands.add_parser('brief').add_argument('--archive', action='store_true')
    listing = commands.add_parser('list')
    listing.add_argument('--kind')
    listing.add_argument('--state')
    listing.add_argument('--all', action='store_true')
    for name in ('show', 'done', 'ignore', 'reopen', 'draft', 'cancel'):
        commands.add_parser(name).add_argument('id')
    snooze = commands.add_parser('snooze')
    snooze.add_argument('id')
    snooze.add_argument('until', help='ISO date/time, tomorrow, 3h or 2d')
    add = commands.add_parser('add')
    add.add_argument('kind', choices=['reply', 'commitment', 'appointment', 'waiting'])
    add.add_argument('title')
    add.add_argument('--contact')
    add.add_argument('--due')
    add.add_argument('--due-text')
    commands.add_parser('contacts').add_argument('text')
    link = commands.add_parser('link')
    link.add_argument('channel')
    link.add_argument('address')
    link.add_argument('contact_id')
    link.add_argument('--reject', action='store_true')
    commands.add_parser('import-contacts').add_argument('csv', nargs='?')
    for name in ('pause', 'resume', 'export', 'serve-mcp'):
        commands.add_parser(name)
    args = parser.parse_args(argv)

    if args.command == 'status':
        for key, value in api.status().items():
            if key != 'email_accounts':
                print(f'{key.replace("_", " "):24} {value}')
    elif args.command == 'scan':
        print(json.dumps(scan.run(), indent=2))
    elif args.command == 'brief':
        print(api.current_brief(save=args.archive)['brief'])
    elif args.command == 'list':
        show_items(api.list_items(args.kind, args.state, include_closed=args.all))
    elif args.command == 'show':
        print(json.dumps(api.get_item(args.id), indent=2, ensure_ascii=False))
    elif args.command in ('done', 'ignore', 'reopen', 'cancel'):
        action = {'done': api.mark_done, 'ignore': api.ignore_item, 'reopen': api.reopen_item,
                  'cancel': api.cancel_commitment}[args.command]
        item = action(args.id)
        print(f'{item["id"]}: {item["state"].lower()}')
    elif args.command == 'snooze':
        item = api.snooze_item(args.id, args.until)
        print(f'{item["id"]}: snoozed until {item["snoozed_until"]}')
    elif args.command == 'draft':
        print(api.draft_reply(args.id)['draft'])
    elif args.command == 'add':
        item = api.create_item(args.kind, args.title, contact=args.contact, due=args.due, due_text=args.due_text)
        print(f'{item["id"]}: {item["state"].lower()}')
    elif args.command == 'contacts':
        print(json.dumps(api.get_contact_state(args.text), indent=2, ensure_ascii=False))
    elif args.command == 'link':
        print(api.link_contact(args.channel, args.address, args.contact_id, 'reject' if args.reject else 'confirm'))
    elif args.command == 'import-contacts':
        print(api.import_contacts(args.csv))
    elif args.command in ('pause', 'resume'):
        print(api.set_paused(args.command == 'pause'))
    elif args.command == 'export':
        print(export.write_all())
    elif args.command == 'serve-mcp':
        from .mcp_server import serve
        serve()


if __name__ == '__main__':
    main()
