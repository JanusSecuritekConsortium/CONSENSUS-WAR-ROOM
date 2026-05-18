import curses
import time
import random
import json
from pyfiglet import Figlet

def load_theme_from_file():
    try:
        with open("theme_boot_sequences.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def draw_banner(stdscr, lines):
    h, w = stdscr.getmaxyx()
    for idx, line in enumerate(lines):
        stdscr.addstr(h//2 - len(lines)//2 + idx, max(0, (w - len(line)) // 2), line)
        stdscr.refresh()
        time.sleep(0.2)

def draw_boot_steps(stdscr, steps):
    h, w = stdscr.getmaxyx()
    for i, step in enumerate(steps):
        line = f"[ ... ] {step}"
        stdscr.addstr(h//2 + i + 5, 4, line)
        stdscr.refresh()
        time.sleep(0.3)
        stdscr.addstr(h//2 + i + 5, 4, line.replace("[ ... ]", "[  OK  ]"))
        stdscr.refresh()
        time.sleep(0.2)

def main(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()

    theme_data = load_theme_from_file()
    if not theme_data:
        stdscr.addstr(0, 0, "Failed to load theme_boot_sequences.json")
        stdscr.refresh()
        stdscr.getch()
        return

    selected_theme = random.choice(list(theme_data.keys()))
    text = theme_data[selected_theme]["text"]
    font = theme_data[selected_theme]["font"]
    steps = theme_data[selected_theme].get("boot_steps", [])

    banner = Figlet(font=font).renderText(text)
    lines = banner.splitlines()
    draw_banner(stdscr, lines)
    draw_boot_steps(stdscr, steps)

    final = ">>> PRESS ENTER TO ENTER THE WAR ROOM <<<"
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h-2, max(0, (w - len(final)) // 2), final)
    stdscr.refresh()
    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)