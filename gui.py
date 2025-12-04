import flet as ft
from core import ConfigManager, CheckInManager
import threading
import time
import schedule
from datetime import datetime, timedelta

def main(page: ft.Page):
    page.title = "AutoCheckBJMF - Class Cube Auto Check-in"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed="blue") # Material 3 seed color
    page.window.width = 800
    page.window.height = 800

    config_manager = ConfigManager()

    # Log control
    log_lv = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    def log_callback(message):
        log_lv.controls.append(ft.Text(message, font_family="Consolas", size=12))
        page.update()

    checkin_manager = CheckInManager(config_manager, log_callback=log_callback)

    # --- Settings Controls ---
    class_id = ft.TextField(label="Class ID", value=config_manager.get("class"))
    lat = ft.TextField(label="Latitude", value=config_manager.get("lat"), expand=True)
    lng = ft.TextField(label="Longitude", value=config_manager.get("lng"), expand=True)
    acc = ft.TextField(label="Altitude", value=config_manager.get("acc"), expand=True)

    cookies_val = "\n".join(config_manager.get("cookie", []))
    cookies = ft.TextField(
        label="Cookies (one per line, support 'username=<name>;cookie...')",
        value=cookies_val,
        multiline=True,
        min_lines=5,
        max_lines=10,
        text_size=12
    )

    schedule_time = ft.TextField(
        label="Schedule Time (HH:MM, leave empty to disable)",
        value=config_manager.get("scheduletime"),
        hint_text="08:00"
    )
    push_token = ft.TextField(label="PushPlus Token", value=config_manager.get("pushplus"))
    debug_mode = ft.Switch(label="Debug Mode", value=config_manager.get("debug"))

    def save_settings(e):
        new_cookies = [c.strip() for c in cookies.value.split("\n") if c.strip()]
        data = {
            "class": class_id.value,
            "lat": lat.value,
            "lng": lng.value,
            "acc": acc.value,
            "cookie": new_cookies,
            "scheduletime": schedule_time.value,
            "pushplus": push_token.value,
            "debug": debug_mode.value,
            "configLock": True
        }
        config_manager.save_config(data)

        # Update scheduler
        update_schedule_task()

        page.show_snack_bar(ft.SnackBar(content=ft.Text("Settings saved!")))

    save_btn = ft.FilledButton("Save Settings", on_click=save_settings, icon=ft.icons.SAVE)

    settings_view = ft.Container(
        content=ft.Column([
            ft.Text("Configuration", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            class_id,
            ft.Row([lat, lng, acc]),
            cookies,
            schedule_time,
            push_token,
            debug_mode,
            ft.Divider(),
            ft.Row([save_btn], alignment=ft.MainAxisAlignment.END)
        ], scroll=ft.ScrollMode.AUTO),
        padding=20
    )

    # --- Dashboard Controls ---
    status_text = ft.Text("Ready", size=16)
    countdown_text = ft.Text("", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.PRIMARY)

    def run_checkin(e):
        run_btn.disabled = True
        page.update()
        threading.Thread(target=run_checkin_thread).start()

    def run_checkin_thread():
        log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Starting manual check-in...")
        checkin_manager.run_job()
        run_btn.disabled = False
        log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual check-in finished.")
        page.update()

    run_btn = ft.FloatingActionButton(text="Run Now", on_click=run_checkin, icon=ft.icons.PLAY_ARROW)

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
        ]),
        padding=20,
        expand=True
    )

    def clean_logs():
        log_lv.controls.clear()
        page.update()

    # --- Scheduler Logic ---
    scheduler_running = False

    def update_schedule_task():
        schedule.clear()
        time_str = config_manager.get("scheduletime")
        if time_str:
            try:
                # Validation
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
                    page.update()
                except:
                    countdown_text.value = ""
            else:
                countdown_text.value = ""
                page.update()

            time.sleep(1)

    # Initialize scheduler
    update_schedule_task()
    threading.Thread(target=scheduler_loop, daemon=True).start()

    # --- Main Layout ---

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="Dashboard", icon=ft.icons.DASHBOARD, content=dashboard_view),
            ft.Tab(text="Settings", icon=ft.icons.SETTINGS, content=settings_view),
        ],
        expand=True,
    )

    page.add(tabs)
    page.floating_action_button = run_btn

ft.app(target=main)
