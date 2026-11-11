#!/usr/bin/python3
"""Keyboard launcher for Google, Codex and Claude."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlencode

HOME = Path.home()
TARGETS = ('Google', 'Codex', 'Claude')
# Codex and Claude start here instead of the home folder: Claude Code never
# remembers trust for the home folder, so it asked on every launch. Ignored by git.
WORKSPACE = Path(__file__).resolve().parent / 'workspace'
LOG_FILE = (Path(os.environ.get('XDG_STATE_HOME') or HOME / '.local/state')
            / 'quick-search' / 'quick-search.log')
log = logging.getLogger('quick-search')


def setup_logging():
    """Log to LOG_FILE (rotated, so it stays small), including unexpected errors."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=256_000, backupCount=1)
    except OSError:
        handler = logging.StreamHandler()  # The log file can't be written; use stderr.
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

    # Errors inside GTK callbacks are otherwise only printed to stderr.
    default_hook = sys.excepthook

    def log_unexpected(*exc_info):
        log.critical('Unexpected error', exc_info=exc_info)
        default_hook(*exc_info)

    sys.excepthook = log_unexpected


def launch(target, prompt):
    # The prompt itself is never logged.
    if target == 'Google':
        log.info('Opening Google search')
        subprocess.Popen(['xdg-open', 'https://www.google.com/search?' + urlencode({'q': prompt})])
        return
    # Check ~/.local/bin before PATH: both CLIs install there, and the PATH
    # given to a GNOME custom shortcut may not include it.
    executable = HOME / '.local/bin' / target.lower()
    if not (executable.is_file() and os.access(executable, os.X_OK)):
        executable = shutil.which(target.lower())
    if not executable:
        raise RuntimeError(f'{target} is not installed.')
    terminal = shutil.which('ptyxis')
    if not terminal:
        raise RuntimeError('Ptyxis terminal was not found.')
    WORKSPACE.mkdir(exist_ok=True)
    log.info('Opening %s (%s) in Ptyxis', target, executable)
    # Argument arrays preserve quotes, newlines and shell characters literally.
    subprocess.Popen([terminal, '--new-window', '--working-directory=' + str(WORKSPACE),
                      '--', str(executable), '--', prompt], cwd=WORKSPACE)


def main():
    setup_logging()
    # GTK is imported here rather than at the top so launch() can be imported
    # and tested without a display; Launcher is defined here because it needs Gtk.
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, Gio, GLib

    class Launcher(Gtk.Application):
        def __init__(self):
            super().__init__(application_id='local.quicksearch.Launcher',
                             flags=Gio.ApplicationFlags.FLAGS_NONE)
            self.window = None

        def do_activate(self):
            if self.window is not None:
                self.window.present()
                return
            self.window = Gtk.ApplicationWindow(application=self, title='Quick Search')
            self.window.set_default_size(540, 250)
            self.window.set_resizable(False)
            self.window.set_position(Gtk.WindowPosition.CENTER)
            self.window.connect('key-press-event', self.key_pressed)
            self.window.connect('focus-out-event', self.focus_out)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            box.set_border_width(20)
            self.window.add(box)
            self.entry = Gtk.Entry()
            self.entry.set_placeholder_text('Search Google or ask Codex / Claude…')
            self.entry.connect('activate', self.submit)
            self.entry.connect('changed', lambda *_: self.error.hide())
            box.pack_start(self.entry, False, False, 0)
            self.choices = Gtk.ListBox()
            # BROWSE keeps exactly one row selected; SINGLE allows none.
            self.choices.set_selection_mode(Gtk.SelectionMode.BROWSE)
            for name in TARGETS:
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=name, xalign=0)
                label.set_margin_start(12)
                label.set_margin_top(8)
                label.set_margin_bottom(8)
                row.add(label)
                self.choices.add(row)
            self.choices.select_row(self.choices.get_row_at_index(0))
            self.choices.connect('row-activated', lambda *_: self.submit())
            box.pack_start(self.choices, False, False, 0)
            # Hidden until opening something fails.
            self.error = Gtk.Label(xalign=0, selectable=True)
            self.error.set_line_wrap(True)
            self.error.set_no_show_all(True)
            box.pack_start(self.error, False, False, 0)
            self.status = Gtk.Label(label='↑ ↓ Choose · Enter Open · Esc Close', xalign=0)
            box.pack_start(self.status, False, False, 0)
            self.window.show_all()
            self.entry.grab_focus()
            self.window.present()

        def key_pressed(self, window, event):
            if event.keyval == Gdk.KEY_Escape:
                self.quit()
                return True
            if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
                index = self.choices.get_selected_row().get_index()
                index = (index + (1 if event.keyval == Gdk.KEY_Down else -1)) % len(TARGETS)
                self.choices.select_row(self.choices.get_row_at_index(index))
                return True
            return False

        def focus_out(self, *_):
            # Clicking another window closes the launcher. The entry's right-click
            # menu also takes focus, so stay open while that menu is showing.
            if Gtk.grab_get_current() is None:
                self.quit()
            return False

        def show_error(self, message):
            log_path = (f'~/{LOG_FILE.relative_to(HOME)}' if LOG_FILE.is_relative_to(HOME)
                        else str(LOG_FILE))
            self.error.set_markup(
                f'<span foreground="#e01b24">{GLib.markup_escape_text(message)}</span>\n'
                f'<small>See the log: {GLib.markup_escape_text(log_path)}</small>')
            self.error.show()

        def submit(self, *_):
            prompt = self.entry.get_text().strip()
            if not prompt:
                self.entry.grab_focus()
                return
            target = TARGETS[self.choices.get_selected_row().get_index()]
            try:
                launch(target, prompt)
            except Exception as error:
                log.exception('Could not open %s', target)
                self.show_error(str(error) or type(error).__name__)
                return
            self.quit()

    return Launcher().run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
