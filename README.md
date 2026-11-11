# Quick Search

A native GTK launcher for Google, Codex and Claude. Uses the installed CLIs and
their existing login/configuration. Google opens in your default browser.

## Run

```sh
git clone https://github.com/Stoky555/quick-search.git
/usr/bin/python3 quick-search/quick_search.py
```

Type a prompt, choose with Up/Down, and press Enter. Google is selected initially.
Escape, or clicking another window, closes the launcher. Repeating the shortcut
presents the existing window. AI conversations open in Ptyxis, starting in the
`workspace/` folder next to `quick_search.py` (created on first use and ignored
by git), so each CLI asks once whether to trust it instead of on every launch.
You can put your own `CLAUDE.md` or `AGENTS.md` there. They retain their normal
permission prompts. This launcher does not infer the active project.

If something can't be opened, the error appears under the list along with the
log location: `~/.local/state/quick-search/quick-search.log`. Prompts are not
written to the log.

## Keyboard shortcut

Ubuntu Settings → Keyboard → View and Customize Shortcuts → Custom Shortcuts:

- Name: Quick Search
- Command: `/usr/bin/python3 /home/<you>/quick-search/quick_search.py`
  (use the full path to wherever you cloned it)
- Shortcut: Ctrl+Alt+Space (or another unused combination)

No autostart service is needed. GNOME handles the global shortcut on Wayland.

## Dependencies

System Python 3, PyGObject / GTK 3, Ptyxis, xdg-open, and the CLIs you want to
use (`codex`, `claude`).
