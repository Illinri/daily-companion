import customtkinter as ctk
import sqlite3
import os
import json
from datetime import datetime, date
import calendar

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

# ── Database ───────────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        archived INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS daily_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL UNIQUE,
        success INTEGER,          -- 1=yes, 0=no, NULL=not logged
        note TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL,
        content TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT DEFAULT ''
    )""")
    # seed notes row if empty
    c.execute("SELECT COUNT(*) FROM notes")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO notes (content) VALUES ('')")
    con.commit()
    con.close()

def get_con():
    return sqlite3.connect(DB_PATH)

# ── Colour palette ─────────────────────────────────────────────────────────────
BG        = "#1a1a2e"
PANEL     = "#16213e"
CARD      = "#0f3460"
ACCENT    = "#e94560"
TEXT      = "#eaeaea"
MUTED     = "#888"
GREEN     = "#4caf50"
RED       = "#e94560"
GREY      = "#444"
SIDEBAR_W = 64

# ── Reusable widgets ───────────────────────────────────────────────────────────
class Divider(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, height=1, fg_color="#333", **kw)

class SectionTitle(ctk.CTkLabel):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, text=text,
                         font=ctk.CTkFont(size=18, weight="bold"),
                         text_color=TEXT, **kw)

# ── Goals panel ────────────────────────────────────────────────────────────────
class GoalsPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        SectionTitle(self, text="🎯  Goals").pack(anchor="w", padx=24, pady=(24, 4))
        Divider(self).pack(fill="x", padx=24, pady=(0, 16))

        # ── add goal form ──
        form = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        form.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkLabel(form, text="New goal", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=MUTED).pack(anchor="w", padx=16, pady=(12, 0))

        self.goal_name = ctk.CTkEntry(form, placeholder_text="Goal name…",
                                      fg_color=CARD, border_width=0,
                                      text_color=TEXT, height=36)
        self.goal_name.pack(fill="x", padx=16, pady=(8, 0))

        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(8, 12))

        self.goal_dur = ctk.CTkEntry(row, placeholder_text="Duration (days)",
                                     fg_color=CARD, border_width=0,
                                     text_color=TEXT, height=36, width=160)
        self.goal_dur.pack(side="left")

        ctk.CTkButton(row, text="Add Goal", fg_color=ACCENT, hover_color="#c73652",
                      height=36, corner_radius=8,
                      command=self._add_goal).pack(side="right")

        # ── existing goals ──
        con = get_con()
        goals = con.execute(
            "SELECT id, name, duration_days, start_date FROM goals WHERE archived=0 ORDER BY id DESC"
        ).fetchall()
        con.close()

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, label_text="")
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        if not goals:
            ctk.CTkLabel(scroll, text="No goals yet — add one above.",
                         text_color=MUTED).pack(pady=20)
        else:
            for gid, name, dur, start in goals:
                self._goal_card(scroll, gid, name, dur, start)

    def _goal_card(self, parent, gid, name, dur, start):
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=12)
        card.pack(fill="x", pady=6)

        start_dt = date.fromisoformat(start)
        elapsed  = (date.today() - start_dt).days
        progress = min(elapsed / max(dur, 1), 1.0)
        pct      = int(progress * 100)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(header, text=name,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(side="left")
        ctk.CTkLabel(header, text=f"{min(elapsed, dur)}/{dur} days",
                     text_color=MUTED, font=ctk.CTkFont(size=12)).pack(side="right")

        bar = ctk.CTkProgressBar(card, height=8, corner_radius=4,
                                  progress_color=GREEN if pct >= 100 else ACCENT)
        bar.pack(fill="x", padx=16, pady=(0, 4))
        bar.set(progress)

        ctk.CTkLabel(card, text=f"{pct}% complete",
                     text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)

        ctk.CTkButton(card, text="Archive", fg_color="transparent",
                      text_color=MUTED, hover_color=GREY, height=24,
                      font=ctk.CTkFont(size=11),
                      command=lambda i=gid: self._archive(i)).pack(anchor="e", padx=12, pady=(0, 8))

    def _add_goal(self):
        name = self.goal_name.get().strip()
        dur  = self.goal_dur.get().strip()
        if not name or not dur.isdigit():
            return
        con = get_con()
        con.execute("INSERT INTO goals (name, duration_days, start_date) VALUES (?,?,?)",
                    (name, int(dur), date.today().isoformat()))
        con.commit()
        con.close()
        self.goal_name.delete(0, "end")
        self.goal_dur.delete(0, "end")
        self._build()

    def _archive(self, gid):
        con = get_con()
        con.execute("UPDATE goals SET archived=1 WHERE id=?", (gid,))
        con.commit()
        con.close()
        self._build()

# ── Today panel ────────────────────────────────────────────────────────────────
class TodayPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        today = date.today().isoformat()
        con   = get_con()
        row   = con.execute(
            "SELECT success, note FROM daily_logs WHERE log_date=?", (today,)
        ).fetchone()
        con.close()

        SectionTitle(self, text="📅  Today").pack(anchor="w", padx=24, pady=(24, 4))
        ctk.CTkLabel(self, text=datetime.now().strftime("%A, %B %d %Y"),
                     text_color=MUTED).pack(anchor="w", padx=24, pady=(0, 4))
        Divider(self).pack(fill="x", padx=24, pady=(0, 24))

        card = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        card.pack(fill="x", padx=24)

        ctk.CTkLabel(card, text="How did today go?",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).pack(pady=(20, 12))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(pady=(0, 16))

        logged = row is not None and row[0] is not None
        yes_color = GREEN  if (logged and row[0] == 1) else CARD
        no_color  = RED    if (logged and row[0] == 0) else CARD

        ctk.CTkButton(btn_row, text="✅  Yes", fg_color=yes_color,
                      hover_color="#2e7d32", width=110, height=44,
                      font=ctk.CTkFont(size=15),
                      command=lambda: self._log(1)).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="❌  No",  fg_color=no_color,
                      hover_color="#b71c1c", width=110, height=44,
                      font=ctk.CTkFont(size=15),
                      command=lambda: self._log(0)).pack(side="left", padx=8)

        ctk.CTkLabel(card, text="Quick note (optional):",
                     text_color=MUTED, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20)

        self.note_box = ctk.CTkTextbox(card, height=90, fg_color=CARD,
                                        border_width=0, text_color=TEXT)
        self.note_box.pack(fill="x", padx=20, pady=(4, 16))

        if row and row[1]:
            self.note_box.insert("0.0", row[1])

        ctk.CTkButton(card, text="Save note", fg_color=ACCENT,
                      hover_color="#c73652", height=34, corner_radius=8,
                      command=self._save_note).pack(anchor="e", padx=20, pady=(0, 16))

        # streak
        con   = get_con()
        logs  = con.execute(
            "SELECT log_date, success FROM daily_logs WHERE success IS NOT NULL ORDER BY log_date DESC"
        ).fetchall()
        con.close()
        streak = 0
        for ld, s in logs:
            if s == 1:
                streak += 1
            else:
                break

        ctk.CTkLabel(self, text=f"🔥 Current streak: {streak} day{'s' if streak != 1 else ''}",
                     font=ctk.CTkFont(size=13),
                     text_color=TEXT).pack(anchor="w", padx=24, pady=(20, 0))

    def _log(self, val):
        today = date.today().isoformat()
        con   = get_con()
        existing = con.execute(
            "SELECT note FROM daily_logs WHERE log_date=?", (today,)
        ).fetchone()
        note = existing[0] if existing and existing[0] else ""
        con.execute(
            "INSERT INTO daily_logs (log_date, success, note) VALUES (?,?,?) "
            "ON CONFLICT(log_date) DO UPDATE SET success=excluded.success",
            (today, val, note)
        )
        con.commit()
        con.close()
        self._build()

    def _save_note(self):
        today = date.today().isoformat()
        note  = self.note_box.get("0.0", "end").strip()
        con   = get_con()
        con.execute(
            "INSERT INTO daily_logs (log_date, success, note) VALUES (?,NULL,?) "
            "ON CONFLICT(log_date) DO UPDATE SET note=excluded.note",
            (today, note)
        )
        con.commit()
        con.close()

# ── Journal panel ──────────────────────────────────────────────────────────────
class JournalPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self.selected_date = date.today().isoformat()
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        SectionTitle(self, text="📓  Journal").pack(anchor="w", padx=24, pady=(24, 4))
        Divider(self).pack(fill="x", padx=24, pady=(0, 16))

        # date nav
        nav = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        nav.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkButton(nav, text="◀", width=32, fg_color="transparent",
                      text_color=TEXT, command=self._prev_day).pack(side="left", padx=8, pady=8)

        self.date_label = ctk.CTkLabel(nav,
            text=datetime.strptime(self.selected_date, "%Y-%m-%d").strftime("%B %d, %Y"),
            font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT)
        self.date_label.pack(side="left", expand=True)

        ctk.CTkButton(nav, text="▶", width=32, fg_color="transparent",
                      text_color=TEXT, command=self._next_day).pack(side="right", padx=8, pady=8)

        # entry area
        con     = get_con()
        row     = con.execute(
            "SELECT id, content FROM journal WHERE entry_date=?", (self.selected_date,)
        ).fetchone()
        con.close()

        self.journal_box = ctk.CTkTextbox(self, fg_color=PANEL, border_width=0,
                                           text_color=TEXT,
                                           font=ctk.CTkFont(size=13))
        self.journal_box.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        if row:
            self.journal_box.insert("0.0", row[1] or "")

        ctk.CTkButton(self, text="Save Entry", fg_color=ACCENT,
                      hover_color="#c73652", height=36, corner_radius=8,
                      command=self._save).pack(anchor="e", padx=24, pady=(0, 16))

    def _save(self):
        content = self.journal_box.get("0.0", "end").strip()
        con = get_con()
        row = con.execute(
            "SELECT id FROM journal WHERE entry_date=?", (self.selected_date,)
        ).fetchone()
        if row:
            con.execute("UPDATE journal SET content=? WHERE id=?", (content, row[0]))
        else:
            con.execute("INSERT INTO journal (entry_date, content) VALUES (?,?)",
                        (self.selected_date, content))
        con.commit()
        con.close()

    def _prev_day(self):
        self._save()
        from datetime import timedelta
        d = date.fromisoformat(self.selected_date) - timedelta(days=1)
        self.selected_date = d.isoformat()
        self._build()

    def _next_day(self):
        self._save()
        from datetime import timedelta
        d = date.fromisoformat(self.selected_date) + timedelta(days=1)
        self.selected_date = d.isoformat()
        self._build()

# ── Notes panel ────────────────────────────────────────────────────────────────
class NotesPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        SectionTitle(self, text="🗒️  Notes").pack(anchor="w", padx=24, pady=(24, 4))
        Divider(self).pack(fill="x", padx=24, pady=(0, 16))

        con = get_con()
        row = con.execute("SELECT id, content FROM notes LIMIT 1").fetchone()
        con.close()

        self.notes_box = ctk.CTkTextbox(self, fg_color=PANEL, border_width=0,
                                         text_color=TEXT, font=ctk.CTkFont(size=13))
        self.notes_box.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        if row and row[1]:
            self.notes_box.insert("0.0", row[1])

        ctk.CTkButton(self, text="Save Notes", fg_color=ACCENT,
                      hover_color="#c73652", height=36, corner_radius=8,
                      command=self._save).pack(anchor="e", padx=24, pady=(0, 16))

    def _save(self):
        content = self.notes_box.get("0.0", "end").strip()
        con = get_con()
        row = con.execute("SELECT id FROM notes LIMIT 1").fetchone()
        if row:
            con.execute("UPDATE notes SET content=? WHERE id=?", (content, row[0]))
        else:
            con.execute("INSERT INTO notes (content) VALUES (?)", (content,))
        con.commit()
        con.close()

# ── Calendar panel ─────────────────────────────────────────────────────────────
class CalendarPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        today       = date.today()
        self.year   = today.year
        self.month  = today.month
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        SectionTitle(self, text="🗓️  Calendar").pack(anchor="w", padx=24, pady=(24, 4))
        Divider(self).pack(fill="x", padx=24, pady=(0, 8))

        # month nav
        nav = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        nav.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkButton(nav, text="◀", width=32, fg_color="transparent",
                      text_color=TEXT, command=self._prev_month).pack(side="left", padx=8, pady=8)

        ctk.CTkLabel(nav,
            text=date(self.year, self.month, 1).strftime("%B %Y"),
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT
        ).pack(side="left", expand=True)

        ctk.CTkButton(nav, text="▶", width=32, fg_color="transparent",
                      text_color=TEXT, command=self._next_month).pack(side="right", padx=8, pady=8)

        # fetch logs for this month
        con = get_con()
        prefix = f"{self.year}-{str(self.month).zfill(2)}"
        rows   = con.execute(
            "SELECT log_date, success FROM daily_logs WHERE log_date LIKE ?",
            (f"{prefix}%",)
        ).fetchall()
        con.close()
        log_map = {r[0]: r[1] for r in rows}

        # day-of-week headers
        grid = ctk.CTkFrame(self, fg_color=BG)
        grid.pack(fill="x", padx=24)

        for col, day in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            ctk.CTkLabel(grid, text=day, width=44, text_color=MUTED,
                         font=ctk.CTkFont(size=11)).grid(row=0, column=col, padx=2, pady=2)

        # day cells
        today         = date.today()
        first_wd, days_in_month = calendar.monthrange(self.year, self.month)
        row_num = 1
        col_num = first_wd  # Monday=0

        for day_num in range(1, days_in_month + 1):
            d_str   = f"{self.year}-{str(self.month).zfill(2)}-{str(day_num).zfill(2)}"
            success = log_map.get(d_str)  # 1, 0, or None

            if success == 1:
                color = GREEN
            elif success == 0:
                color = RED
            else:
                color = GREY if date(self.year, self.month, day_num) < today else CARD

            is_today = (self.year == today.year and
                        self.month == today.month and
                        day_num == today.day)

            btn = ctk.CTkButton(
                grid, text=str(day_num), width=44, height=36,
                fg_color=color,
                border_width=2 if is_today else 0,
                border_color=TEXT if is_today else color,
                corner_radius=8,
                font=ctk.CTkFont(size=12, weight="bold" if is_today else "normal"),
                text_color=TEXT,
                hover_color=color
            )
            btn.grid(row=row_num, column=col_num, padx=2, pady=2)

            col_num += 1
            if col_num > 6:
                col_num = 0
                row_num += 1

        # legend
        legend = ctk.CTkFrame(self, fg_color=BG)
        legend.pack(anchor="w", padx=24, pady=(16, 0))
        for color, label in [(GREEN, "Success"), (RED, "Miss"), (GREY, "No log")]:
            dot = ctk.CTkFrame(legend, width=12, height=12, corner_radius=6, fg_color=color)
            dot.pack(side="left", padx=(0, 4))
            ctk.CTkLabel(legend, text=label, text_color=MUTED,
                         font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 12))

    def _prev_month(self):
        if self.month == 1:
            self.month, self.year = 12, self.year - 1
        else:
            self.month -= 1
        self._build()

    def _next_month(self):
        if self.month == 12:
            self.month, self.year = 1, self.year + 1
        else:
            self.month += 1
        self._build()

# ── Main window ────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    PANELS = [
        ("🎯", "Goals",    GoalsPanel),
        ("📅", "Today",    TodayPanel),
        ("📓", "Journal",  JournalPanel),
        ("🗒️", "Notes",    NotesPanel),
        ("🗓️", "Calendar", CalendarPanel),
    ]

    def __init__(self):
        super().__init__()
        self.title("Daily Companion")
        self.geometry("780x620")
        self.minsize(680, 500)
        self.configure(fg_color=BG)

        # keep on top toggle (Windows)
        self._on_top = False
        self._build()
        self._show(0)

    def _build(self):
        # ── sidebar ──
        sidebar = ctk.CTkFrame(self, width=SIDEBAR_W, fg_color=PANEL, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._nav_btns = []
        for i, (icon, label, _) in enumerate(self.PANELS):
            btn = ctk.CTkButton(
                sidebar, text=icon, width=SIDEBAR_W, height=52,
                fg_color="transparent", hover_color=CARD,
                font=ctk.CTkFont(size=20), text_color=TEXT,
                corner_radius=0,
                command=lambda i=i: self._show(i)
            )
            btn.pack(pady=2)
            btn.bind("<Enter>", lambda e, l=label, b=btn: self._tooltip(b, l))
            self._nav_btns.append(btn)

        # pin-to-top button at bottom of sidebar
        ctk.CTkButton(
            sidebar, text="📌", width=SIDEBAR_W, height=44,
            fg_color="transparent", hover_color=CARD,
            font=ctk.CTkFont(size=18), text_color=MUTED,
            corner_radius=0, command=self._toggle_top
        ).pack(side="bottom", pady=8)

        # ── content area ──
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        self._current_panel = None

    def _show(self, index):
        if self._current_panel:
            self._current_panel.destroy()

        for i, btn in enumerate(self._nav_btns):
            btn.configure(fg_color=CARD if i == index else "transparent")

        _, _, PanelClass = self.PANELS[index]
        self._current_panel = PanelClass(self.content)
        self._current_panel.pack(fill="both", expand=True)

    def _toggle_top(self):
        self._on_top = not self._on_top
        self.attributes("-topmost", self._on_top)

    def _tooltip(self, widget, text):
        pass  # tooltips optional — labels visible on hover via title bar

if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
