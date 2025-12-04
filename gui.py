import flet as ft
from core import ConfigManager, CheckInManager
import threading
import time
import schedule
from datetime import datetime, timedelta

def main(page: ft.Page):
    page.title = "AutoCheckBJMF - Class Cube Auto Check-in"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed="blue")
    page.window.width = 1100
    page.window.height = 800

    config_manager = ConfigManager()

    # Log control
    log_lv = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    def log_callback(message):
        color = ft.colors.ON_SURFACE
        if "❌" in message or "失败" in message or "Error" in message or "无效" in message:
            color = ft.colors.ERROR
        elif "✅" in message or "成功" in message:
            color = ft.colors.GREEN

        log_lv.controls.append(ft.Text(message, font_family="Consolas", size=12, color=color))
        log_lv.update()
        log_lv.scroll_to(offset=-1, animate=True)

    checkin_manager = CheckInManager(config_manager, log_callback=log_callback)

    # ==========================
    # Tab 1: Dashboard
    # ==========================
    status_text = ft.Text("Ready", size=16)
    countdown_text = ft.Text("", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.PRIMARY)

    def run_checkin(e):
        run_btn.disabled = True
        run_btn.update()
        threading.Thread(target=run_checkin_thread).start()

    def run_checkin_thread():
        log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Starting manual check-in...")
        try:
            checkin_manager.run_job()
            log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual check-in finished.")
        except Exception as ex:
            log_callback(f"Critical Error: {ex}")

        run_btn.disabled = False
        run_btn.update()

    run_btn = ft.FloatingActionButton(text="Run Now", on_click=run_checkin, icon=ft.icons.PLAY_ARROW)

    def clean_logs():
        log_lv.controls.clear()
        page.update()

    dashboard_view = ft.Container(
        content=ft.Column([
            ft.Text("Dashboard", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.TIMER),
                            title=ft.Text("Schedule Status"),
                            subtitle=status_text
                        ),
                        ft.Container(
                            content=countdown_text,
                            padding=ft.padding.only(left=70, bottom=10)
                        )
                    ]),
                    padding=10
                )
            ),
            ft.Container(height=20),
            ft.Row([
                ft.Text("Logs:", style=ft.TextThemeStyle.TITLE_MEDIUM),
                ft.IconButton(icon=ft.icons.CLEAR_ALL, tooltip="Clear Logs", on_click=lambda e: clean_logs())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=log_lv,
                expand=True,
                border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                border_radius=10,
                padding=10,
                bgcolor=ft.colors.with_opacity(0.3, ft.colors.SURFACE_VARIANT)
            )
        ], expand=True),
        padding=20,
        expand=True
    )

    # ==========================
    # Tab 2: Accounts Management
    # ==========================
    accounts_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def refresh_accounts_list():
        accounts_column.controls.clear()
        accounts = config_manager.get("accounts", [])

        for idx, acc in enumerate(accounts):
            card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.PERSON, color=ft.colors.BLUE),
                        ft.Column([
                            ft.Text(acc.get("name", "Account"), weight=ft.FontWeight.BOLD, size=16),
                            ft.Text(f"Class: {acc.get('class_id')}", size=12, color=ft.colors.OUTLINE)
                        ], expand=True),
                        ft.IconButton(ft.icons.EDIT, on_click=lambda e, i=idx: edit_account(i)),
                        ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: delete_account(i)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15
                )
            )
            accounts_column.controls.append(card)
        page.update()

    def delete_account(idx):
        accounts = config_manager.get("accounts", [])
        if 0 <= idx < len(accounts):
            del accounts[idx]
            config_manager.save_config({"accounts": accounts})
            refresh_accounts_list()
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Account deleted")))

    # Account Dialog
    acc_name = ft.TextField(label="Name (Remark)", expand=True)
    acc_class_id = ft.TextField(label="Class ID")
    acc_cookie = ft.TextField(label="Cookie", multiline=True, min_lines=3)
    acc_pwd = ft.TextField(label="Sign Password (Optional)", password=True)

    current_acc_idx = -1

    def save_account_dialog(e):
        accounts = config_manager.get("accounts", [])
        new_acc = {
            "name": acc_name.value,
            "class_id": acc_class_id.value,
            "cookie": acc_cookie.value.strip(),
            "pwd": acc_pwd.value
        }

        if current_acc_idx >= 0:
            accounts[current_acc_idx] = new_acc
        else:
            accounts.append(new_acc)

        config_manager.save_config({"accounts": accounts})
        acc_dialog.open = False
        refresh_accounts_list()
        page.update()

    acc_dialog = ft.AlertDialog(
        title=ft.Text("Edit Account"),
        content=ft.Column([acc_name, acc_class_id, acc_cookie, acc_pwd], tight=True, width=500),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: setattr(acc_dialog, 'open', False) or page.update()),
            ft.TextButton("Save", on_click=save_account_dialog),
        ],
    )

    def edit_account(idx):
        nonlocal current_acc_idx
        current_acc_idx = idx
        accounts = config_manager.get("accounts", [])
        if idx == -1:
            # Add
            acc_name.value = ""
            acc_class_id.value = ""
            acc_cookie.value = ""
            acc_pwd.value = ""
            acc_dialog.title = ft.Text("Add Account")
        else:
            # Edit
            acc = accounts[idx]
            acc_name.value = acc.get("name", "")
            acc_class_id.value = acc.get("class_id", "")
            acc_cookie.value = acc.get("cookie", "")
            acc_pwd.value = acc.get("pwd", "")
            acc_dialog.title = ft.Text("Edit Account")

        page.dialog = acc_dialog
        acc_dialog.open = True
        page.update()

    accounts_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Accounts", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.FilledButton("Add Account", icon=ft.icons.ADD, on_click=lambda e: edit_account(-1))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            accounts_column
        ], expand=True),
        padding=20,
        expand=True
    )

    # ==========================
    # Tab 3: Locations Management
    # ==========================
    locations_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def refresh_locations_list():
        locations_column.controls.clear()
        locations = config_manager.get("locations", [])

        for idx, loc in enumerate(locations):
            card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.LOCATION_ON, color=ft.colors.RED),
                        ft.Column([
                            ft.Text(loc.get("name", "Location"), weight=ft.FontWeight.BOLD, size=16),
                            ft.Text(f"Lat: {loc.get('lat')}, Lng: {loc.get('lng')}", size=12, color=ft.colors.OUTLINE)
                        ], expand=True),
                        ft.IconButton(ft.icons.EDIT, on_click=lambda e, i=idx: edit_location(i)),
                        ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: delete_location(i)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15
                )
            )
            locations_column.controls.append(card)
        page.update()

    def delete_location(idx):
        locations = config_manager.get("locations", [])
        if 0 <= idx < len(locations):
            del locations[idx]
            config_manager.save_config({"locations": locations})
            refresh_locations_list()
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Location deleted")))

    # Location Dialog
    loc_name = ft.TextField(label="Name (e.g. Building A)", expand=True)
    loc_lat = ft.TextField(label="Latitude", expand=True)
    loc_lng = ft.TextField(label="Longitude", expand=True)
    loc_acc = ft.TextField(label="Accuracy/Altitude", value="0.0")

    current_loc_idx = -1

    def save_location_dialog(e):
        locations = config_manager.get("locations", [])
        new_loc = {
            "name": loc_name.value,
            "lat": loc_lat.value,
            "lng": loc_lng.value,
            "acc": loc_acc.value
        }

        if current_loc_idx >= 0:
            locations[current_loc_idx] = new_loc
        else:
            locations.append(new_loc)

        config_manager.save_config({"locations": locations})
        loc_dialog.open = False
        refresh_locations_list()
        page.update()

    loc_dialog = ft.AlertDialog(
        title=ft.Text("Edit Location"),
        content=ft.Column([loc_name, ft.Row([loc_lat, loc_lng]), loc_acc], tight=True, width=500),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: setattr(loc_dialog, 'open', False) or page.update()),
            ft.TextButton("Save", on_click=save_location_dialog),
        ],
    )

    def edit_location(idx):
        nonlocal current_loc_idx
        current_loc_idx = idx
        locations = config_manager.get("locations", [])
        if idx == -1:
            loc_name.value = ""
            loc_lat.value = ""
            loc_lng.value = ""
            loc_acc.value = "0.0"
            loc_dialog.title = ft.Text("Add Location")
        else:
            loc = locations[idx]
            loc_name.value = loc.get("name", "")
            loc_lat.value = loc.get("lat", "")
            loc_lng.value = loc.get("lng", "")
            loc_acc.value = loc.get("acc", "")
            loc_dialog.title = ft.Text("Edit Location")

        page.dialog = loc_dialog
        loc_dialog.open = True
        page.update()

    locations_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Locations", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.FilledButton("Add Location", icon=ft.icons.ADD, on_click=lambda e: edit_location(-1))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            locations_column
        ], expand=True),
        padding=20,
        expand=True
    )

    # ==========================
    # Tab 4: Tasks Management
    # ==========================
    tasks_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def refresh_tasks_list():
        tasks_column.controls.clear()
        tasks = config_manager.get("tasks", [])

        for idx, task in enumerate(tasks):
            is_enabled = task.get("enable", True)
            status_color = ft.colors.GREEN if is_enabled else ft.colors.GREY

            card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.TASK, color=status_color),
                        ft.Column([
                            ft.Text(f"{task.get('account_name')} @ {task.get('location_name')}", weight=ft.FontWeight.BOLD, size=16),
                            ft.Text("Click Edit to change details", size=12, color=ft.colors.OUTLINE)
                        ], expand=True),
                        ft.Switch(value=is_enabled, on_change=lambda e, i=idx: toggle_task(i, e.control.value)),
                        ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: delete_task(i)),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15
                )
            )
            tasks_column.controls.append(card)
        page.update()

    def delete_task(idx):
        tasks = config_manager.get("tasks", [])
        if 0 <= idx < len(tasks):
            del tasks[idx]
            config_manager.save_config({"tasks": tasks})
            refresh_tasks_list()
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Task deleted")))

    def toggle_task(idx, val):
        tasks = config_manager.get("tasks", [])
        if 0 <= idx < len(tasks):
            tasks[idx]["enable"] = val
            config_manager.save_config({"tasks": tasks})
            refresh_tasks_list()

    # Task Dialog
    task_account_dd = ft.Dropdown(label="Select Account", expand=True)
    task_location_dd = ft.Dropdown(label="Select Location", expand=True)

    def save_task_dialog(e):
        if not task_account_dd.value or not task_location_dd.value:
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Please select both Account and Location")))
            return

        tasks = config_manager.get("tasks", [])
        new_task = {
            "account_name": task_account_dd.value,
            "location_name": task_location_dd.value,
            "enable": True
        }

        tasks.append(new_task)
        config_manager.save_config({"tasks": tasks})
        task_dialog.open = False
        refresh_tasks_list()
        page.update()

    task_dialog = ft.AlertDialog(
        title=ft.Text("Add Task"),
        content=ft.Column([task_account_dd, task_location_dd], tight=True, width=400),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: setattr(task_dialog, 'open', False) or page.update()),
            ft.TextButton("Add", on_click=save_task_dialog),
        ],
    )

    def open_task_dialog():
        # Populate Dropdowns
        accs = config_manager.get("accounts", [])
        locs = config_manager.get("locations", [])

        task_account_dd.options = [ft.dropdown.Option(a.get("name")) for a in accs]
        task_location_dd.options = [ft.dropdown.Option(l.get("name")) for l in locs]

        task_account_dd.value = None
        task_location_dd.value = None

        page.dialog = task_dialog
        task_dialog.open = True
        page.update()

    tasks_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Tasks", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.FilledButton("Add Task", icon=ft.icons.ADD, on_click=lambda e: open_task_dialog())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            tasks_column
        ], expand=True),
        padding=20,
        expand=True
    )

    # ==========================
    # Tab 5: Settings
    # ==========================

    st_schedule_time = ft.TextField(
        label="Global Schedule Time (HH:MM)",
        value=config_manager.get("scheduletime"),
        hint_text="08:00"
    )

    # WeCom Settings
    wecom_conf = config_manager.get("wecom", {})
    st_wecom_corpid = ft.TextField(label="WeCom CorpID", value=wecom_conf.get("corpid"))
    st_wecom_secret = ft.TextField(label="WeCom Secret", value=wecom_conf.get("secret"), password=True, can_reveal_password=True)
    st_wecom_agentid = ft.TextField(label="WeCom AgentID", value=wecom_conf.get("agentid"))
    st_wecom_touser = ft.TextField(label="WeCom ToUser (default @all)", value=wecom_conf.get("touser", "@all"))

    st_debug_mode = ft.Switch(label="Debug Mode", value=config_manager.get("debug"))

    def save_global_settings(e):
        data = {
            "scheduletime": st_schedule_time.value,
            "wecom": {
                "corpid": st_wecom_corpid.value,
                "secret": st_wecom_secret.value,
                "agentid": st_wecom_agentid.value,
                "touser": st_wecom_touser.value
            },
            "debug": st_debug_mode.value,
            "configLock": True
        }
        config_manager.save_config(data)
        update_schedule_task()
        page.show_snack_bar(ft.SnackBar(content=ft.Text("Global settings saved!")))

    settings_view = ft.Container(
        content=ft.Column([
            ft.Text("Global Settings", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            st_schedule_time,
            ft.Divider(),
            ft.Text("WeCom Notification", style=ft.TextThemeStyle.TITLE_MEDIUM),
            st_wecom_corpid,
            st_wecom_secret,
            st_wecom_agentid,
            st_wecom_touser,
            ft.Divider(),
            st_debug_mode,
            ft.Container(height=20),
            ft.FilledButton("Save Global Settings", icon=ft.icons.SAVE, on_click=save_global_settings)
        ], scroll=ft.ScrollMode.AUTO, expand=True),
        padding=20,
        expand=True
    )

    # ==========================
    # Scheduler Logic
    # ==========================
    scheduler_running = False

    def update_schedule_task():
        schedule.clear()
        time_str = config_manager.get("scheduletime")
        if time_str:
            try:
                datetime.strptime(time_str, "%H:%M")
                schedule.every().day.at(time_str).do(scheduled_job)
                status_text.value = f"Scheduled daily at {time_str}"
            except ValueError:
                status_text.value = "Invalid time format (use HH:MM)"
        else:
            status_text.value = "No schedule set (Manual mode)"
        page.update()

    def scheduled_job():
        log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scheduled check-in...")
        checkin_manager.run_job()
        log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduled check-in finished.")

    def scheduler_loop():
        nonlocal scheduler_running
        scheduler_running = True
        while True:
            schedule.run_pending()

            # Update countdown
            time_str = config_manager.get("scheduletime")
            if time_str:
                try:
                    target_time = datetime.strptime(time_str, "%H:%M").time()
                    now = datetime.now()
                    target_dt = datetime.combine(now.date(), target_time)
                    if target_dt < now:
                        target_dt += timedelta(days=1)

                    diff = target_dt - now
                    hours, remainder = divmod(diff.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    countdown_text.value = f"Next run in: {hours:02d}:{minutes:02d}:{seconds:02d}"
                    countdown_text.update()
                except:
                    countdown_text.value = ""
                    countdown_text.update()
            else:
                countdown_text.value = ""
                countdown_text.update()

            time.sleep(1)

    # Initialize
    refresh_accounts_list()
    refresh_locations_list()
    refresh_tasks_list()
    update_schedule_task()

    # --- Main Navigation ---
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="Dashboard", icon=ft.icons.DASHBOARD, content=dashboard_view),
            ft.Tab(text="Tasks", icon=ft.icons.TASK, content=tasks_view),
            ft.Tab(text="Accounts", icon=ft.icons.PERSON, content=accounts_view),
            ft.Tab(text="Locations", icon=ft.icons.LOCATION_ON, content=locations_view),
            ft.Tab(text="Settings", icon=ft.icons.SETTINGS, content=settings_view),
        ],
        expand=True,
    )

    page.add(tabs)
    page.floating_action_button = run_btn

    # Start scheduler after UI is built
    threading.Thread(target=scheduler_loop, daemon=True).start()

ft.app(target=main)
