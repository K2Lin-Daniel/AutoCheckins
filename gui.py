import tkinter as tk
from tkinter import scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.toast import ToastNotification
import threading
import time
import logging
import traceback
import sys
import os
import schedule
from datetime import datetime, timedelta
from core import ConfigManager, CheckInManager

"""
Modern GUI module for AutoCheckBJMF using ttkbootstrap.
Implements Material Design 3 style visuals.
"""

# Determine log path based on execution environment
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

log_path = os.path.join(base_dir, 'gui_tk_debug.log')

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("GUI_MODERN")

class AutoCheckApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="cosmo", title="AutoCheckBJMF - Class Cube", resizable=(True, True))
        self.geometry("1000x700")

        # Initialize Managers
        self.config_manager = ConfigManager()
        self.checkin_manager = CheckInManager(self.config_manager, log_callback=self.log_callback)

        self.create_widgets()
        self.start_scheduler()

    def create_widgets(self):
        # Main Container
        main_container = ttk.Frame(self, padding=20)
        main_container.pack(fill=BOTH, expand=YES)

        # Title Header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=X, pady=(0, 20))
        ttk.Label(header_frame, text="AutoCheckBJMF", font=("Roboto", 24, "bold"), bootstyle=PRIMARY).pack(side=LEFT)
        ttk.Label(header_frame, text="v2.0 Modern UI", font=("Roboto", 10), bootstyle=SECONDARY).pack(side=LEFT, padx=10, pady=(12, 0))

        # Navigation (Notebook) with modern style
        self.notebook = ttk.Notebook(main_container, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES)

        # Tabs
        self.tab_dashboard = ttk.Frame(self.notebook, padding=20)
        self.tab_tasks = ttk.Frame(self.notebook, padding=20)
        self.tab_accounts = ttk.Frame(self.notebook, padding=20)
        self.tab_locations = ttk.Frame(self.notebook, padding=20)
        self.tab_settings = ttk.Frame(self.notebook, padding=20)

        self.notebook.add(self.tab_dashboard, text='Dashboard')
        self.notebook.add(self.tab_tasks, text='Tasks')
        self.notebook.add(self.tab_accounts, text='Accounts')
        self.notebook.add(self.tab_locations, text='Locations')
        self.notebook.add(self.tab_settings, text='Settings')

        # Bind events
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.build_dashboard()
        self.build_tasks()
        self.build_accounts()
        self.build_locations()
        self.build_settings()

    def on_tab_change(self, event):
        tab_name = self.notebook.tab(self.notebook.select(), "text")
        if tab_name == "Tasks":
            self.refresh_tasks()
        elif tab_name == "Accounts":
            self.refresh_accounts()
        elif tab_name == "Locations":
            self.refresh_locations()

    # --- Dashboard ---
    def build_dashboard(self):
        frame = self.tab_dashboard

        # Top Section: Status Cards
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=X, pady=(0, 20))

        # Card 1: Countdown
        card1 = ttk.Labelframe(status_frame, text="Next Run", padding=15, bootstyle="info")
        card1.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))

        self.lbl_countdown = ttk.Label(card1, text="-", font=("Roboto", 28, "bold"), bootstyle="info")
        self.lbl_countdown.pack(anchor=CENTER, pady=10)
        self.lbl_schedule_info = ttk.Label(card1, text="Initializing...", bootstyle="secondary")
        self.lbl_schedule_info.pack(anchor=CENTER)

        # Card 2: Actions
        card2 = ttk.Labelframe(status_frame, text="Quick Actions", padding=15, bootstyle="secondary")
        card2.pack(side=LEFT, fill=BOTH, expand=YES, padx=(10, 0))

        self.btn_run = ttk.Button(card2, text="Run Check-in Now", command=self.run_manual_checkin, bootstyle="success-outline", width=20)
        self.btn_run.pack(pady=5, fill=X)

        ttk.Button(card2, text="Clear Logs", command=self.clear_logs, bootstyle="secondary-outline", width=20).pack(pady=5, fill=X)

        # Bottom Section: Logs
        log_frame = ttk.Labelframe(frame, text="Activity Logs", padding=10, bootstyle="default")
        log_frame.pack(fill=BOTH, expand=YES)

        self.txt_log = scrolledtext.ScrolledText(log_frame, state='disabled', font=('Consolas', 10), height=15)
        self.txt_log.pack(fill=BOTH, expand=YES)

        # Styles for log
        self.txt_log.tag_config('error', foreground='#dc3545') # Bootstrap Danger
        self.txt_log.tag_config('success', foreground='#198754') # Bootstrap Success
        self.txt_log.tag_config('warning', foreground='#ffc107') # Bootstrap Warning
        self.txt_log.tag_config('normal', foreground='#212529') # Dark

    def log_callback(self, message):
        def _update():
            self.txt_log.config(state='normal')

            tag = 'normal'
            if any(x in message for x in ["❌", "失败", "Error", "Exception"]):
                tag = 'error'
            elif any(x in message for x in ["✅", "成功", "Finished"]):
                tag = 'success'
            elif any(x in message for x in ["Warning", "⚠️"]):
                tag = 'warning'

            self.txt_log.insert(tk.END, message + "\n", tag)
            self.txt_log.see(tk.END)
            self.txt_log.config(state='disabled')

        self.after(0, _update)

    def clear_logs(self):
        self.txt_log.config(state='normal')
        self.txt_log.delete(1.0, tk.END)
        self.txt_log.config(state='disabled')
        ToastNotification(title="Logs Cleared", message="Log window has been cleared.", duration=2000, bootstyle="light").show_toast()

    def run_manual_checkin(self):
        self.btn_run.config(state='disabled')
        ToastNotification(title="Started", message="Manual check-in process started.", duration=3000, bootstyle="success").show_toast()
        threading.Thread(target=self._run_checkin_thread, daemon=True).start()

    def _run_checkin_thread(self):
        self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual run started...")
        try:
            self.checkin_manager.run_job()
            self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual run completed.")
        except Exception as e:
            self.log_callback(f"Error: {e}")
            logger.error(traceback.format_exc())
            self.after(0, lambda: Messagebox.show_error(f"An error occurred: {e}", "Error"))

        self.after(0, lambda: self.btn_run.config(state='normal'))

    # --- Tasks ---
    def build_tasks(self):
        frame = self.tab_tasks

        # Toolbar
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Button(toolbar, text="Add Task", command=self.add_task, bootstyle="primary").pack(side=LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Delete Task", command=self.delete_task, bootstyle="danger-outline").pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="Toggle Enable", command=self.toggle_task, bootstyle="warning-outline").pack(side=LEFT, padx=5)

        # Table
        cols = ('Account', 'Location', 'Status')
        self.tree_tasks = ttk.Treeview(frame, columns=cols, show='headings', bootstyle="primary")
        for col in cols:
            self.tree_tasks.heading(col, text=col)
            self.tree_tasks.column(col, width=150)

        self.tree_tasks.pack(fill=BOTH, expand=YES)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree_tasks, orient=VERTICAL, command=self.tree_tasks.yview)
        self.tree_tasks.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

    def refresh_tasks(self):
        for i in self.tree_tasks.get_children():
            self.tree_tasks.delete(i)

        tasks = self.config_manager.get("tasks", [])
        for idx, task in enumerate(tasks):
            status = "Active" if task.get("enable", True) else "Disabled"
            self.tree_tasks.insert('', 'end', iid=idx, values=(
                task.get('account_name', '?'),
                task.get('location_name', '?'),
                status
            ))

    def add_task(self):
        accs = self.config_manager.get("accounts", [])
        locs = self.config_manager.get("locations", [])

        if not accs or not locs:
            Messagebox.show_warning("Please add Accounts and Locations first.", "Missing Data")
            return

        acc_names = [a.get("name") for a in accs]
        loc_names = [l.get("name") for l in locs]

        # Dialog
        dialog = ttk.Toplevel(title="Add Task")
        dialog.geometry("400x250")

        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=BOTH, expand=YES)

        ttk.Label(content, text="Select Account", bootstyle="primary").pack(anchor=W, pady=(0, 5))
        cb_acc = ttk.Combobox(content, values=acc_names, state="readonly")
        cb_acc.pack(fill=X, pady=(0, 15))

        ttk.Label(content, text="Select Location", bootstyle="primary").pack(anchor=W, pady=(0, 5))
        cb_loc = ttk.Combobox(content, values=loc_names, state="readonly")
        cb_loc.pack(fill=X, pady=(0, 15))

        def save():
            if not cb_acc.get() or not cb_loc.get():
                Messagebox.show_warning("Please select both fields.", "Invalid Input", parent=dialog)
                return
            tasks = self.config_manager.get("tasks", [])
            tasks.append({
                "account_name": cb_acc.get(),
                "location_name": cb_loc.get(),
                "enable": True
            })
            self.config_manager.save_config({"tasks": tasks})
            self.refresh_tasks()
            dialog.destroy()
            ToastNotification("Task Added", "New task created successfully.", bootstyle="success").show_toast()

        ttk.Button(content, text="Save Task", command=save, bootstyle="success").pack(fill=X, pady=10)

    def delete_task(self):
        selected = self.tree_tasks.selection()
        if not selected:
            return

        if Messagebox.okcancel("Are you sure you want to delete this task?", "Confirm Delete"):
            idx = int(selected[0])
            tasks = self.config_manager.get("tasks", [])
            if 0 <= idx < len(tasks):
                del tasks[idx]
                self.config_manager.save_config({"tasks": tasks})
                self.refresh_tasks()

    def toggle_task(self):
        selected = self.tree_tasks.selection()
        if not selected:
            return

        idx = int(selected[0])
        tasks = self.config_manager.get("tasks", [])
        if 0 <= idx < len(tasks):
            tasks[idx]["enable"] = not tasks[idx].get("enable", True)
            self.config_manager.save_config({"tasks": tasks})
            self.refresh_tasks()

    # --- Accounts ---
    def build_accounts(self):
        frame = self.tab_accounts

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Button(toolbar, text="Add Account", command=lambda: self.open_account_dialog(-1), bootstyle="primary").pack(side=LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Edit Account", command=self.edit_account, bootstyle="info-outline").pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="Delete Account", command=self.delete_account, bootstyle="danger-outline").pack(side=LEFT, padx=5)

        cols = ('Name', 'Class ID', 'Cookie Preview')
        self.tree_accounts = ttk.Treeview(frame, columns=cols, show='headings', bootstyle="info")
        for col in cols:
            self.tree_accounts.heading(col, text=col)
        self.tree_accounts.column('Cookie Preview', width=300)

        self.tree_accounts.pack(fill=BOTH, expand=YES)

    def refresh_accounts(self):
        for i in self.tree_accounts.get_children():
            self.tree_accounts.delete(i)

        accounts = self.config_manager.get("accounts", [])
        for idx, acc in enumerate(accounts):
            cookie_short = (acc.get('cookie', '')[:30] + '...') if len(acc.get('cookie', '')) > 30 else acc.get('cookie', '')
            self.tree_accounts.insert('', 'end', iid=idx, values=(
                acc.get('name', ''),
                acc.get('class_id', ''),
                cookie_short
            ))

    def edit_account(self):
        selected = self.tree_accounts.selection()
        if selected:
            self.open_account_dialog(int(selected[0]))

    def open_account_dialog(self, idx):
        accounts = self.config_manager.get("accounts", [])
        is_edit = idx >= 0
        data = accounts[idx] if is_edit else {}

        dialog = ttk.Toplevel(title="Edit Account" if is_edit else "Add Account")
        dialog.geometry("500x550")

        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=BOTH, expand=YES)

        # Helper to create fields
        def create_field(parent, label, value, is_password=False, is_multiline=False):
            ttk.Label(parent, text=label, bootstyle="primary").pack(anchor=W, pady=(10, 5))
            if is_multiline:
                txt = scrolledtext.ScrolledText(parent, height=5, font=('Consolas', 9))
                txt.insert(1.0, value)
                txt.pack(fill=X)
                return txt
            else:
                entry = ttk.Entry(parent, show="*" if is_password else None)
                entry.insert(0, value)
                entry.pack(fill=X)
                return entry

        entry_name = create_field(content, "Name", data.get("name", ""))
        entry_class = create_field(content, "Class ID", data.get("class_id", ""))
        txt_cookie = create_field(content, "Cookie", data.get("cookie", ""), is_multiline=True)
        entry_pwd = create_field(content, "Password (Optional - for pwd check-in)", data.get("pwd", ""), is_password=True)

        def save():
            name_val = entry_name.get().strip()
            class_val = entry_class.get().strip()
            cookie_val = txt_cookie.get(1.0, tk.END).strip()

            if not name_val or not class_val or not cookie_val:
                Messagebox.show_warning("Name, Class ID and Cookie are required.", "Invalid Input", parent=dialog)
                return

            new_acc = {
                "name": name_val,
                "class_id": class_val,
                "cookie": cookie_val,
                "pwd": entry_pwd.get().strip()
            }
            if is_edit:
                accounts[idx] = new_acc
            else:
                accounts.append(new_acc)
            self.config_manager.save_config({"accounts": accounts})
            self.refresh_accounts()
            dialog.destroy()
            ToastNotification("Saved", "Account saved successfully.", bootstyle="success").show_toast()

        ttk.Button(content, text="Save Account", command=save, bootstyle="success").pack(fill=X, pady=20)

    def delete_account(self):
        selected = self.tree_accounts.selection()
        if not selected:
            return

        if Messagebox.okcancel("Delete this account?", "Confirm"):
            idx = int(selected[0])
            accounts = self.config_manager.get("accounts", [])
            if 0 <= idx < len(accounts):
                del accounts[idx]
                self.config_manager.save_config({"accounts": accounts})
                self.refresh_accounts()

    # --- Locations ---
    def build_locations(self):
        frame = self.tab_locations

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Button(toolbar, text="Add Location", command=lambda: self.open_location_dialog(-1), bootstyle="primary").pack(side=LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Edit Location", command=self.edit_location, bootstyle="info-outline").pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="Delete Location", command=self.delete_location, bootstyle="danger-outline").pack(side=LEFT, padx=5)

        cols = ('Name', 'Lat', 'Lng', 'Acc')
        self.tree_locations = ttk.Treeview(frame, columns=cols, show='headings', bootstyle="success")
        for col in cols:
            self.tree_locations.heading(col, text=col)

        self.tree_locations.pack(fill=BOTH, expand=YES)

    def refresh_locations(self):
        for i in self.tree_locations.get_children():
            self.tree_locations.delete(i)

        locations = self.config_manager.get("locations", [])
        for idx, loc in enumerate(locations):
            self.tree_locations.insert('', 'end', iid=idx, values=(
                loc.get('name', ''),
                loc.get('lat', ''),
                loc.get('lng', ''),
                loc.get('acc', '')
            ))

    def edit_location(self):
        selected = self.tree_locations.selection()
        if selected:
            self.open_location_dialog(int(selected[0]))

    def open_location_dialog(self, idx):
        locations = self.config_manager.get("locations", [])
        is_edit = idx >= 0
        data = locations[idx] if is_edit else {}

        dialog = ttk.Toplevel(title="Edit Location" if is_edit else "Add Location")
        dialog.geometry("400x400")

        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=BOTH, expand=YES)

        def create_entry(label, val):
            ttk.Label(content, text=label, bootstyle="primary").pack(anchor=W, pady=(10, 5))
            e = ttk.Entry(content)
            e.insert(0, val)
            e.pack(fill=X)
            return e

        e_name = create_entry("Location Name", data.get("name", ""))
        e_lat = create_entry("Latitude", data.get("lat", ""))
        e_lng = create_entry("Longitude", data.get("lng", ""))
        e_acc = create_entry("Accuracy", data.get("acc", "0.0"))

        def save():
            try:
                # Basic validation
                float(e_lat.get())
                float(e_lng.get())
            except ValueError:
                Messagebox.show_error("Latitude and Longitude must be numbers.", "Validation Error", parent=dialog)
                return

            new_loc = {
                "name": e_name.get(),
                "lat": e_lat.get(),
                "lng": e_lng.get(),
                "acc": e_acc.get()
            }
            if is_edit:
                locations[idx] = new_loc
            else:
                locations.append(new_loc)
            self.config_manager.save_config({"locations": locations})
            self.refresh_locations()
            dialog.destroy()
            ToastNotification("Saved", "Location saved successfully.", bootstyle="success").show_toast()

        ttk.Button(content, text="Save Location", command=save, bootstyle="success").pack(fill=X, pady=20)

    def delete_location(self):
        selected = self.tree_locations.selection()
        if not selected:
            return

        if Messagebox.okcancel("Delete this location?", "Confirm"):
            idx = int(selected[0])
            locations = self.config_manager.get("locations", [])
            if 0 <= idx < len(locations):
                del locations[idx]
                self.config_manager.save_config({"locations": locations})
                self.refresh_locations()

    # --- Settings ---
    def build_settings(self):
        frame = self.tab_settings
        wecom = self.config_manager.get("wecom", {})

        # Settings Container
        container = ttk.Frame(frame, padding=20)
        container.pack(fill=BOTH, expand=YES)

        # Section 1: Scheduler
        sec1 = ttk.Labelframe(container, text="Scheduling", padding=15, bootstyle="info")
        sec1.pack(fill=X, pady=(0, 20))

        ttk.Label(sec1, text="Daily Run Time (HH:MM)").pack(anchor=W)
        self.entry_sched = ttk.Entry(sec1)
        self.entry_sched.insert(0, self.config_manager.get("scheduletime", "08:00"))
        self.entry_sched.pack(fill=X, pady=(5, 0))

        # Section 2: Notifications (WeCom)
        sec2 = ttk.Labelframe(container, text="WeCom Notification (Enterprise WeChat)", padding=15, bootstyle="info")
        sec2.pack(fill=X, pady=(0, 20))

        def add_field(parent, label, key, show=None):
            ttk.Label(parent, text=label).pack(anchor=W, pady=(10, 0))
            e = ttk.Entry(parent, show=show)
            e.insert(0, wecom.get(key, ""))
            e.pack(fill=X, pady=(5, 0))
            return e

        self.entry_corpid = add_field(sec2, "Corp ID", "corpid")
        self.entry_secret = add_field(sec2, "Secret", "secret", show="*")
        self.entry_agentid = add_field(sec2, "Agent ID", "agentid")
        self.entry_touser = add_field(sec2, "To User (e.g., @all)", "touser")

        # Section 3: Debug
        self.var_debug = tk.BooleanVar(value=self.config_manager.get("debug", False))
        ttk.Checkbutton(container, text="Enable Debug Logging", variable=self.var_debug, bootstyle="round-toggle").pack(anchor=W, pady=10)

        ttk.Button(container, text="Save All Settings", command=self.save_settings, bootstyle="success").pack(fill=X, pady=20)

    def save_settings(self):
        try:
            # Validate Time
            datetime.strptime(self.entry_sched.get(), "%H:%M")
        except ValueError:
            Messagebox.show_error("Invalid time format. Please use HH:MM.", "Error")
            return

        new_conf = {
            "scheduletime": self.entry_sched.get(),
            "wecom": {
                "corpid": self.entry_corpid.get(),
                "secret": self.entry_secret.get(),
                "agentid": self.entry_agentid.get(),
                "touser": self.entry_touser.get()
            },
            "debug": self.var_debug.get()
        }
        self.config_manager.save_config(new_conf)
        self.update_scheduler_job()
        ToastNotification("Settings Saved", "Configuration updated successfully.", bootstyle="success").show_toast()

    # --- Scheduler ---
    def start_scheduler(self):
        self.update_scheduler_job()
        threading.Thread(target=self._scheduler_loop, daemon=True).start()

    def update_scheduler_job(self):
        schedule.clear()
        time_str = self.config_manager.get("scheduletime", "08:00")
        try:
            datetime.strptime(time_str, "%H:%M")
            schedule.every().day.at(time_str).do(self._scheduled_job)
            self.lbl_schedule_info.config(text=f"Scheduled daily at {time_str}")
        except ValueError:
            self.lbl_schedule_info.config(text="Invalid time format")

    def _scheduled_job(self):
        threading.Thread(target=self._run_job_thread, daemon=True).start()

    def _run_job_thread(self):
        self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scheduled check-in...")
        try:
            self.checkin_manager.run_job()
            self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduled check-in finished.")
        except Exception as e:
            self.log_callback(f"Error during scheduled job: {e}")
            logger.error(traceback.format_exc())

    def _scheduler_loop(self):
        while True:
            schedule.run_pending()
            self.after(0, self._update_countdown)
            time.sleep(1)

    def _update_countdown(self):
        time_str = self.config_manager.get("scheduletime")
        if not time_str:
            return
        try:
            target_time = datetime.strptime(time_str, "%H:%M").time()
            now = datetime.now()
            target_dt = datetime.combine(now.date(), target_time)
            if target_dt < now:
                target_dt += timedelta(days=1)
            diff = target_dt - now
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.lbl_countdown.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        except:
            pass

if __name__ == "__main__":
    app = AutoCheckApp()
    app.place_window_center()
    app.mainloop()
