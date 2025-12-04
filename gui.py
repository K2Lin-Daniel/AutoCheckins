import flet as ft
import threading
import time
import logging
import traceback
import multiprocessing
import schedule
import sys
import os
from datetime import datetime, timedelta
from core import ConfigManager, CheckInManager

"""
GUI module for AutoCheckBJMF.

This module provides a graphical user interface using the Flet framework
to manage configuration (accounts, locations, tasks) and monitor check-in status.
"""

# Determine log path based on execution environment (script vs frozen exe)
if getattr(sys, 'frozen', False):
    # Running as PyInstaller executable
    base_dir = os.path.dirname(sys.executable)
else:
    # Running as script
    base_dir = os.path.dirname(os.path.abspath(__file__))

log_path = os.path.join(base_dir, 'gui_debug.log')

# Configure logging to file for debugging GUI startup issues
# We use force=True because core.py might have already configured logging
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("GUI")

class BJMFApp:
    """
    The main application class for the AutoCheckBJMF GUI.

    Manages the application state, UI components, and interactions between
    the user and the core logic (ConfigManager, CheckInManager).
    """
    def __init__(self, page: ft.Page):
        """
        Initialize the BJMFApp.

        Args:
            page (ft.Page): The Flet page object.
        """
        self.page = page
        self.config_manager = ConfigManager()
        self.checkin_manager = CheckInManager(self.config_manager, log_callback=self.log_callback)
        self.scheduler_running = True

        # State variables
        self.current_view_index = 0
        self.countdown_text = ft.Text("-", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.PRIMARY)
        self.status_text = ft.Text("Ready", size=16)
        self.log_list = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        self.run_btn = ft.FilledButton(
            "Run Check-in Now",
            icon=ft.icons.PLAY_CIRCLE_OUTLINE,
            on_click=self.run_manual_checkin
        )

        self.setup_page()
        self.build_ui()
        self.start_scheduler()

    def setup_page(self):
        """
        Configure general page properties such as title, theme, and window size.
        """
        self.page.title = "AutoCheckBJMF - Class Cube"
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.theme = ft.Theme(color_scheme_seed=ft.colors.PINK)
        self.page.window.width = 1000
        self.page.window.height = 700
        self.page.window.min_width = 800
        self.page.window.min_height = 600
        self.page.padding = 0

    def build_ui(self):
        """
        Construct the main user interface structure.

        Sets up the navigation rail and the content area with an AnimatedSwitcher.
        """
        # Views
        self.views = [
            self.build_dashboard_view(),
            self.build_tasks_view(),
            self.build_accounts_view(),
            self.build_locations_view(),
            self.build_settings_view()
        ]

        # Navigation Rail
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.icons.DASHBOARD,
                    label="Dashboard"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.TASK_ALT_OUTLINED,
                    selected_icon=ft.icons.TASK_ALT,
                    label="Tasks"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.PERSON_OUTLINE,
                    selected_icon=ft.icons.PERSON,
                    label="Accounts"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.LOCATION_ON_OUTLINED,
                    selected_icon=ft.icons.LOCATION_ON,
                    label="Locations"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SETTINGS_OUTLINED,
                    selected_icon=ft.icons.SETTINGS,
                    label="Settings"
                ),
            ],
            on_change=self.on_nav_change
        )

        # Content Area
        self.content_area = ft.AnimatedSwitcher(
            content=self.views[0],
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=300,
            reverse_duration=300,
            switch_in_curve=ft.AnimationCurve.EASE_IN,
            switch_out_curve=ft.AnimationCurve.EASE_OUT,
            expand=True
        )

        # Main Layout
        self.page.add(
            ft.Row(
                [
                    self.nav_rail,
                    ft.VerticalDivider(width=1),
                    self.content_area
                ],
                expand=True
            )
        )

    def on_nav_change(self, e):
        """
        Handle navigation rail selection changes.

        Args:
            e (ft.ControlEvent): The event object.
        """
        self.current_view_index = e.control.selected_index
        self.content_area.content = self.views[self.current_view_index]
        self.content_area.update()

        # Refresh specific views when accessed
        if self.current_view_index == 1: # Tasks
            self.refresh_tasks_list()
        elif self.current_view_index == 2: # Accounts
            self.refresh_accounts_list()
        elif self.current_view_index == 3: # Locations
            self.refresh_locations_list()

    # --- Dashboard ---
    def build_dashboard_view(self):
        """
        Build the Dashboard view.

        Returns:
            ft.Container: The container holding dashboard controls.
        """
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Dashboard", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                ft.Container(height=10),
                ft.Row([
                    ft.Card(
                        elevation=2,
                        content=ft.Container(
                            padding=20,
                            width=300,
                            content=ft.Column([
                                ft.Icon(ft.icons.TIMER, size=40, color=ft.colors.PRIMARY),
                                ft.Text("Next Run In", weight=ft.FontWeight.BOLD),
                                self.status_text,
                                ft.Divider(),
                                self.countdown_text
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                        )
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.Column([
                            ft.Text("Actions", weight=ft.FontWeight.BOLD),
                            self.run_btn,
                            ft.OutlinedButton(
                                "Clear Logs",
                                icon=ft.icons.DELETE_SWEEP,
                                on_click=lambda e: self.clear_logs()
                            )
                        ], spacing=10)
                    )
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Container(height=20),
                ft.Text("Activity Logs", style=ft.TextThemeStyle.TITLE_MEDIUM),
                ft.Container(
                    content=self.log_list,
                    expand=True,
                    border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=10,
                    bgcolor=ft.colors.SURFACE_VARIANT
                )
            ], expand=True)
        )

    def log_callback(self, message):
        """
        Callback for handling log messages from the core logic.

        Updates the UI log list with colored messages based on content.

        Args:
            message (str): The log message.
        """
        color = ft.colors.ON_SURFACE
        if any(x in message for x in ["❌", "失败", "Error", "无效", "Exception"]):
            color = ft.colors.ERROR
        elif any(x in message for x in ["✅", "成功", "Finished"]):
            color = ft.colors.GREEN

        # Append to UI list safely
        self.log_list.controls.append(ft.Text(message, font_family="Consolas", size=12, color=color))
        # Keep only last 1000 logs to prevent memory issues
        if len(self.log_list.controls) > 1000:
             self.log_list.controls.pop(0)

        try:
            self.log_list.update()
        except Exception:
            pass # Page might be closed

    def clear_logs(self):
        """Clear the log list in the UI."""
        self.log_list.controls.clear()
        self.log_list.update()

    def run_manual_checkin(self, e):
        """
        Trigger a manual check-in run.

        Disables the run button and starts a background thread.

        Args:
            e (ft.ControlEvent): The event object.
        """
        self.run_btn.disabled = True
        self.run_btn.update()
        threading.Thread(target=self._run_checkin_thread, daemon=True).start()

    def _run_checkin_thread(self):
        """Background thread worker for manual check-in execution."""
        self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual run started...")
        try:
            self.checkin_manager.run_job()
            self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual run completed.")
        except Exception as e:
            self.log_callback(f"Error: {e}")
            logger.error(traceback.format_exc())

        self.run_btn.disabled = False
        try:
            self.run_btn.update()
        except:
            pass

    # --- Tasks ---
    def build_tasks_view(self):
        """
        Build the Tasks management view.

        Returns:
            ft.Container: The container holding task controls.
        """
        self.tasks_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Tasks", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                    ft.FilledButton("Add Task", icon=ft.icons.ADD, on_click=self.open_add_task_dialog)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.tasks_column
            ], expand=True)
        )

    def refresh_tasks_list(self):
        """Refreshes the list of tasks displayed in the UI."""
        self.tasks_column.controls.clear()
        tasks = self.config_manager.get("tasks", [])

        if not tasks:
            self.tasks_column.controls.append(ft.Text("No tasks configured."))

        for idx, task in enumerate(tasks):
            is_enabled = task.get("enable", True)
            card = ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.icons.TASK_ALT, color=ft.colors.ON_PRIMARY_CONTAINER if is_enabled else ft.colors.OUTLINE),
                            bgcolor=ft.colors.PRIMARY_CONTAINER if is_enabled else ft.colors.SURFACE_VARIANT,
                            border_radius=50,
                            padding=10
                        ),
                        ft.Column([
                            ft.Text(f"{task.get('account_name', '?')} @ {task.get('location_name', '?')}", weight=ft.FontWeight.BOLD, size=16),
                            ft.Text("Active" if is_enabled else "Disabled", size=12, color=ft.colors.GREEN if is_enabled else ft.colors.OUTLINE)
                        ], expand=True),
                        ft.Switch(value=is_enabled, on_change=lambda e, i=idx: self.toggle_task(i, e.control.value)),
                        ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: self.delete_task(i)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )
            self.tasks_column.controls.append(card)
        self.tasks_column.update()

    def open_add_task_dialog(self, e):
        """
        Open the dialog to add a new task.

        Args:
            e (ft.ControlEvent): The event object.
        """
        accs = self.config_manager.get("accounts", [])
        locs = self.config_manager.get("locations", [])

        if not accs or not locs:
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("Please add Accounts and Locations first.")))
            return

        dd_acc = ft.Dropdown(label="Account", options=[ft.dropdown.Option(a.get("name")) for a in accs], expand=True)
        dd_loc = ft.Dropdown(label="Location", options=[ft.dropdown.Option(l.get("name")) for l in locs], expand=True)

        def save(e):
            if not dd_acc.value or not dd_loc.value:
                return
            tasks = self.config_manager.get("tasks", [])
            tasks.append({
                "account_name": dd_acc.value,
                "location_name": dd_loc.value,
                "enable": True
            })
            self.config_manager.save_config({"tasks": tasks})
            self.page.close(dlg)
            self.refresh_tasks_list()

        dlg = ft.AlertDialog(
            title=ft.Text("New Task"),
            content=ft.Container(height=150, content=ft.Column([dd_acc, dd_loc])),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dlg)),
                ft.FilledButton("Save", on_click=save)
            ]
        )
        self.page.open(dlg)

    def toggle_task(self, idx, value):
        """
        Toggle the enabled state of a task.

        Args:
            idx (int): The index of the task.
            value (bool): The new enabled state.
        """
        tasks = self.config_manager.get("tasks", [])
        if 0 <= idx < len(tasks):
            tasks[idx]["enable"] = value
            self.config_manager.save_config({"tasks": tasks})
            self.refresh_tasks_list()

    def delete_task(self, idx):
        """
        Delete a task.

        Args:
            idx (int): The index of the task to delete.
        """
        tasks = self.config_manager.get("tasks", [])
        if 0 <= idx < len(tasks):
            del tasks[idx]
            self.config_manager.save_config({"tasks": tasks})
            self.refresh_tasks_list()

    # --- Accounts ---
    def build_accounts_view(self):
        """
        Build the Accounts management view.

        Returns:
            ft.Container: The container holding account controls.
        """
        self.accounts_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Accounts", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                    ft.FilledButton("Add Account", icon=ft.icons.ADD, on_click=lambda e: self.open_account_dialog(-1))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.accounts_column
            ], expand=True)
        )

    def refresh_accounts_list(self):
        """Refreshes the list of accounts displayed in the UI."""
        self.accounts_column.controls.clear()
        accounts = self.config_manager.get("accounts", [])
        for idx, acc in enumerate(accounts):
            card = ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.icons.PERSON, color=ft.colors.ON_SECONDARY_CONTAINER),
                            bgcolor=ft.colors.SECONDARY_CONTAINER,
                            border_radius=50,
                            padding=10
                        ),
                        ft.Column([
                            ft.Text(acc.get("name", "Account"), weight=ft.FontWeight.BOLD, size=16),
                            ft.Text(f"Class: {acc.get('class_id')}", size=12, color=ft.colors.OUTLINE)
                        ], expand=True),
                        ft.IconButton(ft.icons.EDIT, on_click=lambda e, i=idx: self.open_account_dialog(i)),
                        ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: self.delete_account(i)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )
            self.accounts_column.controls.append(card)
        self.accounts_column.update()

    def open_account_dialog(self, idx):
        """
        Open the dialog to add or edit an account.

        Args:
            idx (int): The index of the account to edit, or -1 to add a new account.
        """
        accounts = self.config_manager.get("accounts", [])
        is_edit = idx >= 0
        data = accounts[idx] if is_edit else {}

        tf_name = ft.TextField(label="Name", value=data.get("name", ""), expand=True)
        tf_class = ft.TextField(label="Class ID", value=data.get("class_id", ""), expand=True)
        tf_cookie = ft.TextField(label="Cookie", value=data.get("cookie", ""), multiline=True, min_lines=3)
        tf_pwd = ft.TextField(label="Password (Optional)", value=data.get("pwd", ""), password=True, can_reveal_password=True)

        def save(e):
            new_acc = {
                "name": tf_name.value,
                "class_id": tf_class.value,
                "cookie": tf_cookie.value.strip(),
                "pwd": tf_pwd.value
            }
            if is_edit:
                accounts[idx] = new_acc
            else:
                accounts.append(new_acc)
            self.config_manager.save_config({"accounts": accounts})
            self.page.close(dlg)
            self.refresh_accounts_list()

        dlg = ft.AlertDialog(
            title=ft.Text("Edit Account" if is_edit else "Add Account"),
            content=ft.Container(width=500, content=ft.Column([ft.Row([tf_name, tf_class]), tf_cookie, tf_pwd], tight=True)),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dlg)),
                ft.FilledButton("Save", on_click=save)
            ]
        )
        self.page.open(dlg)

    def delete_account(self, idx):
        """
        Delete an account.

        Args:
            idx (int): The index of the account to delete.
        """
        accounts = self.config_manager.get("accounts", [])
        if 0 <= idx < len(accounts):
            del accounts[idx]
            self.config_manager.save_config({"accounts": accounts})
            self.refresh_accounts_list()

    # --- Locations ---
    def build_locations_view(self):
        """
        Build the Locations management view.

        Returns:
            ft.Container: The container holding location controls.
        """
        self.locations_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Locations", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                    ft.FilledButton("Add Location", icon=ft.icons.ADD, on_click=lambda e: self.open_location_dialog(-1))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.locations_column
            ], expand=True)
        )

    def refresh_locations_list(self):
        """Refreshes the list of locations displayed in the UI."""
        self.locations_column.controls.clear()
        locations = self.config_manager.get("locations", [])
        for idx, loc in enumerate(locations):
            card = ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.icons.LOCATION_ON, color=ft.colors.ON_TERTIARY_CONTAINER),
                            bgcolor=ft.colors.TERTIARY_CONTAINER,
                            border_radius=50,
                            padding=10
                        ),
                        ft.Column([
                            ft.Text(loc.get("name", "Location"), weight=ft.FontWeight.BOLD, size=16),
                            ft.Text(f"{loc.get('lat')}, {loc.get('lng')}", size=12, color=ft.colors.OUTLINE)
                        ], expand=True),
                        ft.IconButton(ft.icons.EDIT, on_click=lambda e, i=idx: self.open_location_dialog(i)),
                        ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: self.delete_location(i)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )
            self.locations_column.controls.append(card)
        self.locations_column.update()

    def open_location_dialog(self, idx):
        """
        Open the dialog to add or edit a location.

        Args:
            idx (int): The index of the location to edit, or -1 to add a new location.
        """
        locations = self.config_manager.get("locations", [])
        is_edit = idx >= 0
        data = locations[idx] if is_edit else {}

        tf_name = ft.TextField(label="Name", value=data.get("name", ""), expand=True)
        tf_lat = ft.TextField(label="Lat", value=data.get("lat", ""), expand=True)
        tf_lng = ft.TextField(label="Lng", value=data.get("lng", ""), expand=True)
        tf_acc = ft.TextField(label="Accuracy", value=data.get("acc", "0.0"), expand=True)

        def save(e):
            new_loc = {
                "name": tf_name.value,
                "lat": tf_lat.value,
                "lng": tf_lng.value,
                "acc": tf_acc.value
            }
            if is_edit:
                locations[idx] = new_loc
            else:
                locations.append(new_loc)
            self.config_manager.save_config({"locations": locations})
            self.page.close(dlg)
            self.refresh_locations_list()

        dlg = ft.AlertDialog(
            title=ft.Text("Edit Location" if is_edit else "Add Location"),
            content=ft.Container(width=500, content=ft.Column([tf_name, ft.Row([tf_lat, tf_lng]), tf_acc], tight=True)),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dlg)),
                ft.FilledButton("Save", on_click=save)
            ]
        )
        self.page.open(dlg)

    def delete_location(self, idx):
        """
        Delete a location.

        Args:
            idx (int): The index of the location to delete.
        """
        locations = self.config_manager.get("locations", [])
        if 0 <= idx < len(locations):
            del locations[idx]
            self.config_manager.save_config({"locations": locations})
            self.refresh_locations_list()

    # --- Settings ---
    def build_settings_view(self):
        """
        Build the Settings view.

        Returns:
            ft.Container: The container holding settings controls.
        """
        # We need to rebuild these inputs when the view is created to ensure they have latest values
        wecom = self.config_manager.get("wecom", {})

        self.tf_sched = ft.TextField(label="Schedule Time (HH:MM)", value=self.config_manager.get("scheduletime", "08:00"))
        self.tf_corpid = ft.TextField(label="CorpID", value=wecom.get("corpid", ""))
        self.tf_secret = ft.TextField(label="Secret", value=wecom.get("secret", ""), password=True, can_reveal_password=True)
        self.tf_agentid = ft.TextField(label="AgentID", value=wecom.get("agentid", ""))
        self.tf_touser = ft.TextField(label="ToUser", value=wecom.get("touser", "@all"))
        self.sw_debug = ft.Switch(label="Debug Logging", value=self.config_manager.get("debug", False))

        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Global Settings", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                ft.Container(height=10),
                ft.Text("Scheduler", style=ft.TextThemeStyle.TITLE_MEDIUM),
                self.tf_sched,
                ft.Divider(),
                ft.Text("WeCom Notifications", style=ft.TextThemeStyle.TITLE_MEDIUM),
                self.tf_corpid,
                self.tf_secret,
                self.tf_agentid,
                self.tf_touser,
                ft.Divider(),
                self.sw_debug,
                ft.Container(height=20),
                ft.FilledButton("Save Settings", icon=ft.icons.SAVE, on_click=self.save_settings)
            ], scroll=ft.ScrollMode.AUTO, expand=True)
        )

    def save_settings(self, e):
        """
        Save the global settings to configuration.

        Args:
            e (ft.ControlEvent): The event object.
        """
        new_conf = {
            "scheduletime": self.tf_sched.value,
            "wecom": {
                "corpid": self.tf_corpid.value,
                "secret": self.tf_secret.value,
                "agentid": self.tf_agentid.value,
                "touser": self.tf_touser.value
            },
            "debug": self.sw_debug.value
        }
        self.config_manager.save_config(new_conf)
        self.update_scheduler_job()
        self.page.show_snack_bar(ft.SnackBar(content=ft.Text("Settings saved successfully.")))

    # --- Scheduler Logic ---
    def start_scheduler(self):
        """Start the background scheduler thread."""
        self.update_scheduler_job()
        threading.Thread(target=self._scheduler_loop, daemon=True).start()

    def update_scheduler_job(self):
        """Update the scheduled job based on the current configuration."""
        schedule.clear()
        time_str = self.config_manager.get("scheduletime", "08:00")
        try:
            datetime.strptime(time_str, "%H:%M")
            schedule.every().day.at(time_str).do(self._scheduled_job)
            self.status_text.value = f"Scheduled daily at {time_str}"
        except ValueError:
            self.status_text.value = "Invalid time format (HH:MM)"
        self.status_text.update()

    def _scheduled_job(self):
        """The job to be executed by the scheduler."""
        threading.Thread(target=self._run_job_thread, daemon=True).start()

    def _run_job_thread(self):
        """
        Background thread for scheduled job to avoid blocking the scheduler loop
        (and thus the countdown timer).
        """
        self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scheduled check-in...")
        try:
            self.checkin_manager.run_job()
            self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduled check-in finished.")
        except Exception as e:
            self.log_callback(f"Error during scheduled job: {e}")
            logger.error(traceback.format_exc())

    def _scheduler_loop(self):
        """The background loop that keeps the scheduler running."""
        while True:
            schedule.run_pending()
            # Update countdown
            self._update_countdown()
            time.sleep(1)

    def _update_countdown(self):
        """Calculate and update the countdown timer to the next scheduled run."""
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
            self.countdown_text.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            try:
                self.countdown_text.update()
            except:
                pass
        except:
            pass

def main(page: ft.Page):
    """
    The entry point for the Flet application.

    Args:
        page (ft.Page): The Flet page object.
    """
    try:
        BJMFApp(page)
    except Exception as e:
        logger.error(f"Fatal startup error: {traceback.format_exc()}")
        page.add(ft.Text(f"Error starting application: {e}", color="red"))

if __name__ == "__main__":
    # Crucial for PyInstaller compatibility on Windows
    # Must be the very first line after check
    multiprocessing.freeze_support()

    try:
        ft.app(target=main)
    except Exception as e:
        with open("fatal_crash.log", "w") as f:
            f.write(traceback.format_exc())
