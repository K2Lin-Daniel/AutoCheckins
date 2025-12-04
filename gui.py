import flet as ft
from core import ConfigManager, CheckInManager
import threading
import time
import schedule
import logging
import traceback
from datetime import datetime, timedelta

# Configure logging to file for debugging GUI startup issues
logging.basicConfig(filename='gui_debug.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def main(page: ft.Page):
    try:
        logging.info("Starting GUI initialization...")

        # --- Theme & Window Setup ---
        page.title = "AutoCheckBJMF - Class Cube"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.theme = ft.Theme(color_scheme_seed=ft.colors.PINK)
        page.window.width = 1000
        page.window.height = 700
        page.window.min_width = 800
        page.window.min_height = 600
        page.padding = 0  # We will manage padding in the layout

        # --- Core Managers ---
        config_manager = ConfigManager()

        # Log control for the UI
        log_lv = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        def log_callback(message):
            # This callback might be called from background threads
            color = ft.colors.ON_SURFACE
            if "❌" in message or "失败" in message or "Error" in message or "无效" in message:
                color = ft.colors.ERROR
            elif "✅" in message or "成功" in message:
                color = ft.colors.GREEN

            log_lv.controls.append(ft.Text(message, font_family="Consolas", size=12, color=color))
            try:
                log_lv.update()
            except Exception:
                pass # Ignore update errors if page is disposing

        checkin_manager = CheckInManager(config_manager, log_callback=log_callback)

        # --- UI Components Construction ---

        # 1. Dashboard
        status_text = ft.Text("Ready", size=16)
        countdown_text = ft.Text("", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.PRIMARY)

        # Define dashboard run button early so it can be referenced
        dashboard_run_btn = ft.FilledButton(
            "Run Check-in Now",
            icon=ft.icons.PLAY_CIRCLE_OUTLINE,
            style=ft.ButtonStyle(bgcolor=ft.colors.PRIMARY, color=ft.colors.ON_PRIMARY)
        )

        def run_checkin(e):
            dashboard_run_btn.disabled = True
            dashboard_run_btn.update()
            threading.Thread(target=run_checkin_thread).start()

        def run_checkin_thread():
            log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Starting manual check-in...")
            try:
                checkin_manager.run_job()
                log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual check-in finished.")
            except Exception as ex:
                log_callback(f"Critical Error: {ex}")
                logging.error(f"Checkin Error: {ex}")

            dashboard_run_btn.disabled = False
            try:
                dashboard_run_btn.update()
            except:
                pass

        dashboard_run_btn.on_click = run_checkin

        def clean_logs(e):
            log_lv.controls.clear()
            log_lv.update()

        dashboard_view = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Dashboard", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                ft.Container(height=10),
                ft.Row([
                    ft.Card(
                        elevation=2,
                        surface_tint_color=ft.colors.SURFACE_TINT,
                        content=ft.Container(
                            padding=20,
                            width=300,
                            content=ft.Column([
                                ft.Icon(ft.icons.TIMER, size=40, color=ft.colors.PRIMARY),
                                ft.Text("Schedule Status", weight=ft.FontWeight.BOLD),
                                status_text,
                                ft.Divider(),
                                countdown_text
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                        )
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.Column([
                            ft.Text("Actions", weight=ft.FontWeight.BOLD),
                            dashboard_run_btn,
                            ft.OutlinedButton(
                                "Clear Logs",
                                icon=ft.icons.DELETE_SWEEP,
                                on_click=clean_logs
                            )
                        ], spacing=10)
                    )
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Container(height=20),
                ft.Text("Activity Logs", style=ft.TextThemeStyle.TITLE_MEDIUM),
                ft.Container(
                    content=log_lv,
                    expand=True,
                    border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=10,
                    bgcolor=ft.colors.SURFACE_VARIANT
                )
            ], expand=True)
        )

        # 2. Accounts
        accounts_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        acc_name = ft.TextField(label="Name (Remark)", expand=True)
        acc_class_id = ft.TextField(label="Class ID", expand=True)
        acc_cookie = ft.TextField(label="Cookie", multiline=True, min_lines=3)
        acc_pwd = ft.TextField(label="Sign Password (Optional)", password=True, can_reveal_password=True)
        current_acc_idx = -1

        acc_dialog = ft.AlertDialog(
            title=ft.Text("Edit Account"),
            content=ft.Container(
                width=500,
                content=ft.Column([
                    ft.Row([acc_name, acc_class_id]),
                    acc_cookie,
                    acc_pwd
                ], tight=True)
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(acc_dialog)),
                ft.FilledButton("Save", on_click=lambda e: save_account_dialog(e)),
            ],
        )

        def open_acc_dialog(idx):
            nonlocal current_acc_idx
            current_acc_idx = idx
            accounts = config_manager.get("accounts", [])
            if idx == -1:
                acc_name.value = ""
                acc_class_id.value = ""
                acc_cookie.value = ""
                acc_pwd.value = ""
                acc_dialog.title = ft.Text("Add Account")
            else:
                acc = accounts[idx]
                acc_name.value = acc.get("name", "")
                acc_class_id.value = acc.get("class_id", "")
                acc_cookie.value = acc.get("cookie", "")
                acc_pwd.value = acc.get("pwd", "")
                acc_dialog.title = ft.Text("Edit Account")
            page.open(acc_dialog)

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
            page.close(acc_dialog)
            refresh_accounts_list()

        def delete_account(idx):
            accounts = config_manager.get("accounts", [])
            if 0 <= idx < len(accounts):
                del accounts[idx]
                config_manager.save_config({"accounts": accounts})
                refresh_accounts_list()

        def refresh_accounts_list():
            accounts_column.controls.clear()
            accounts = config_manager.get("accounts", [])
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
                            ft.IconButton(ft.icons.EDIT, on_click=lambda e, i=idx: open_acc_dialog(i)),
                            ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: delete_account(i)),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )
                accounts_column.controls.append(card)
            accounts_column.update()

        accounts_view = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Accounts", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                    ft.FilledButton("Add Account", icon=ft.icons.ADD, on_click=lambda e: open_acc_dialog(-1))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                accounts_column
            ], expand=True)
        )

        # 3. Locations
        locations_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        loc_name = ft.TextField(label="Name (e.g. Building A)", expand=True)
        loc_lat = ft.TextField(label="Latitude", expand=True)
        loc_lng = ft.TextField(label="Longitude", expand=True)
        loc_acc = ft.TextField(label="Accuracy/Altitude", value="0.0")
        current_loc_idx = -1

        loc_dialog = ft.AlertDialog(
            title=ft.Text("Edit Location"),
            content=ft.Container(
                width=500,
                content=ft.Column([loc_name, ft.Row([loc_lat, loc_lng]), loc_acc], tight=True)
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(loc_dialog)),
                ft.FilledButton("Save", on_click=lambda e: save_location_dialog(e)),
            ],
        )

        def open_loc_dialog(idx):
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
            page.open(loc_dialog)

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
            page.close(loc_dialog)
            refresh_locations_list()

        def delete_location(idx):
            locations = config_manager.get("locations", [])
            if 0 <= idx < len(locations):
                del locations[idx]
                config_manager.save_config({"locations": locations})
                refresh_locations_list()

        def refresh_locations_list():
            locations_column.controls.clear()
            locations = config_manager.get("locations", [])
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
                                ft.Text(f"Lat: {loc.get('lat')}, Lng: {loc.get('lng')}", size=12, color=ft.colors.OUTLINE)
                            ], expand=True),
                            ft.IconButton(ft.icons.EDIT, on_click=lambda e, i=idx: open_loc_dialog(i)),
                            ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: delete_location(i)),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )
                locations_column.controls.append(card)
            locations_column.update()

        locations_view = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Locations", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                    ft.FilledButton("Add Location", icon=ft.icons.ADD, on_click=lambda e: open_loc_dialog(-1))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                locations_column
            ], expand=True)
        )

        # 4. Tasks
        tasks_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        task_account_dd = ft.Dropdown(label="Select Account", expand=True)
        task_location_dd = ft.Dropdown(label="Select Location", expand=True)

        task_dialog = ft.AlertDialog(
            title=ft.Text("Add Task"),
            content=ft.Container(
                width=400,
                content=ft.Column([task_account_dd, task_location_dd], tight=True)
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(task_dialog)),
                ft.FilledButton("Add", on_click=lambda e: save_task_dialog(e)),
            ],
        )

        def open_task_dialog(e):
            accs = config_manager.get("accounts", [])
            locs = config_manager.get("locations", [])
            task_account_dd.options = [ft.dropdown.Option(a.get("name")) for a in accs]
            task_location_dd.options = [ft.dropdown.Option(l.get("name")) for l in locs]
            task_account_dd.value = None
            task_location_dd.value = None
            page.open(task_dialog)

        def save_task_dialog(e):
            if not task_account_dd.value or not task_location_dd.value:
                page.show_snack_bar(ft.SnackBar(content=ft.Text("Please select both Account and Location")))
                return
            tasks = config_manager.get("tasks", [])
            tasks.append({
                "account_name": task_account_dd.value,
                "location_name": task_location_dd.value,
                "enable": True
            })
            config_manager.save_config({"tasks": tasks})
            page.close(task_dialog)
            refresh_tasks_list()

        def toggle_task(idx, val):
            tasks = config_manager.get("tasks", [])
            if 0 <= idx < len(tasks):
                tasks[idx]["enable"] = val
                config_manager.save_config({"tasks": tasks})
                refresh_tasks_list()

        def delete_task(idx):
            tasks = config_manager.get("tasks", [])
            if 0 <= idx < len(tasks):
                del tasks[idx]
                config_manager.save_config({"tasks": tasks})
                refresh_tasks_list()

        def refresh_tasks_list():
            tasks_column.controls.clear()
            tasks = config_manager.get("tasks", [])
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
                                ft.Text(f"{task.get('account_name')} @ {task.get('location_name')}", weight=ft.FontWeight.BOLD, size=16),
                                ft.Text("Active" if is_enabled else "Disabled", size=12, color=ft.colors.GREEN if is_enabled else ft.colors.OUTLINE)
                            ], expand=True),
                            ft.Switch(value=is_enabled, on_change=lambda e, i=idx: toggle_task(i, e.control.value)),
                            ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e, i=idx: delete_task(i)),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )
                tasks_column.controls.append(card)
            tasks_column.update()

        tasks_view = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Tasks", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                    ft.FilledButton("Add Task", icon=ft.icons.ADD, on_click=open_task_dialog)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                tasks_column
            ], expand=True)
        )

        # 5. Settings
        st_schedule_time = ft.TextField(label="Global Schedule Time (HH:MM)", value=config_manager.get("scheduletime"), hint_text="08:00")
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
                "debug": st_debug_mode.value
            }
            config_manager.save_config(data)
            update_schedule_task()
            page.show_snack_bar(ft.SnackBar(content=ft.Text("Settings saved!")))

        settings_view = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Global Settings", style=ft.TextThemeStyle.HEADLINE_MEDIUM, color=ft.colors.PRIMARY),
                ft.Container(height=10),
                st_schedule_time,
                ft.Divider(),
                ft.Text("WeCom Notification", style=ft.TextThemeStyle.TITLE_MEDIUM),
                st_wecom_corpid,
                st_wecom_secret,
                st_wecom_agentid,
                st_wecom_touser,
                ft.Divider(),
                ft.Row([st_debug_mode]),
                ft.Container(height=20),
                ft.FilledButton("Save Global Settings", icon=ft.icons.SAVE, on_click=save_global_settings)
            ], scroll=ft.ScrollMode.AUTO, expand=True)
        )

        # --- Layout Assembly with NavigationRail ---

        # We need a list of views to switch between
        views = [dashboard_view, tasks_view, accounts_view, locations_view, settings_view]

        def on_nav_change(e):
            selected_index = e.control.selected_index
            content_area.content = views[selected_index]
            content_area.update()

        nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(icon=ft.icons.DASHBOARD_OUTLINED, selected_icon=ft.icons.DASHBOARD, label="Dashboard"),
                ft.NavigationRailDestination(icon=ft.icons.TASK_ALT_OUTLINED, selected_icon=ft.icons.TASK_ALT, label="Tasks"),
                ft.NavigationRailDestination(icon=ft.icons.PERSON_OUTLINE, selected_icon=ft.icons.PERSON, label="Accounts"),
                ft.NavigationRailDestination(icon=ft.icons.LOCATION_ON_OUTLINED, selected_icon=ft.icons.LOCATION_ON, label="Locations"),
                ft.NavigationRailDestination(icon=ft.icons.SETTINGS_OUTLINED, selected_icon=ft.icons.SETTINGS, label="Settings"),
            ],
            on_change=on_nav_change
        )

        content_area = ft.AnimatedSwitcher(
            content=dashboard_view,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=300,
            reverse_duration=300,
            switch_in_curve=ft.AnimationCurve.EASE_IN,
            switch_out_curve=ft.AnimationCurve.EASE_OUT,
            expand=True
        )

        page.add(
            ft.Row(
                [
                    nav_rail,
                    ft.VerticalDivider(width=1),
                    content_area
                ],
                expand=True
            )
        )

        # --- Scheduler ---
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
            try:
                status_text.update()
            except:
                pass

        def scheduled_job():
            log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scheduled check-in...")
            checkin_manager.run_job()
            log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduled check-in finished.")

        def scheduler_loop():
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
                        countdown_text.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        try:
                            countdown_text.update()
                        except:
                            pass
                    except:
                        pass
                time.sleep(1)

        # Init data
        refresh_accounts_list()
        refresh_locations_list()
        refresh_tasks_list()
        update_schedule_task()

        # Start Scheduler Thread
        threading.Thread(target=scheduler_loop, daemon=True).start()

        logging.info("GUI started successfully.")

    except Exception as e:
        logging.error(f"Fatal error in main: {traceback.format_exc()}")
        # Attempt to show error on UI if possible
        try:
            page.clean()
            page.add(ft.Text(f"Fatal Error: {e}", color="red", size=20))
            page.add(ft.Text(traceback.format_exc(), color="red", font_family="Consolas"))
            page.update()
        except:
            pass

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)
