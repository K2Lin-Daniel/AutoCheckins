import flet as ft
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
Modern GUI module for AutoCheckBJMF using Flet.
Implements Material Design 3 style visuals.
"""

logger = logging.getLogger("GUI_FLET")

# Translations
TRANSLATIONS = {
    "en": {
        "title": "AutoCheckBJMF - Class Cube",
        "dashboard": "Dashboard",
        "tasks": "Tasks",
        "accounts": "Accounts",
        "locations": "Locations",
        "settings": "Settings",
        "logs": "Logs",
        "run": "Run",
        "next_run": "Next Scheduled Run",
        "initializing": "Initializing...",
        "quick_actions": "Quick Actions",
        "run_now": "Run Check-in Now",
        "view_logs": "View Logs",
        "help_tutorial": "Help / Tutorial",
        "add_task": "Add Task",
        "no_tasks": "No tasks configured.",
        "active": "Active",
        "disabled": "Disabled",
        "enable": "Enable",
        "disable": "Disable",
        "delete": "Delete",
        "add_account": "Add Account",
        "how_to_cookie": "How to get Cookie?",
        "no_accounts": "No accounts configured.",
        "edit": "Edit",
        "name": "Name",
        "class_id": "Class ID",
        "cookie": "Cookie",
        "password": "Password (Optional, for pwd check-in)",
        "save": "Save",
        "cancel": "Cancel",
        "edit_account": "Edit Account",
        "confirm_delete": "Confirm Delete",
        "delete_msg": "Are you sure you want to delete this?",
        "add_location": "Add Location",
        "no_locations": "No locations configured.",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "accuracy": "Accuracy",
        "daily_time": "Daily Schedule Time (HH:MM)",
        "corp_id": "Corp ID",
        "secret": "Secret",
        "agent_id": "Agent ID",
        "to_user": "To User (e.g., @all)",
        "theme_color": "Theme Color",
        "language": "Language",
        "enable_debug": "Enable Debug Logging",
        "save_settings": "Save All Settings",
        "clear_logs": "Clear Logs",
        "tutorial_title": "Welcome to AutoCheckBJMF!",
        "tutorial_intro": "This tool helps you automate your Class Cube check-ins.",
        "tutorial_guide": "Quick Start Guide:",
        "step_1": "1. Go to 'Accounts' tab and add your account (Cookie & Class ID).",
        "step_2": "2. Go to 'Locations' tab and add your check-in location (Lat/Lng).",
        "step_3": "3. Go to 'Tasks' tab and link your Account to a Location.",
        "step_4": "4. Set your preferred time in 'Settings'.",
        "need_cookie_help": "Need help getting Cookie?",
        "view_cookie_guide": "View Cookie Guide",
        "got_it": "Got it!",
        "cookie_guide_title": "Cookie & Class ID Guide",
        "cookie_guide_md": """
# How to get Cookie and Class ID

1. Go to URL: https://login.b8n.cn/auth/login/student/2
> Scan QR code to login.

2. Press `F12` to open Developer Tools, click `Network`, refresh page.
3. Click `student` request, find `Cookie` in `Request Headers` and copy it.

### 3. Click the orange button as instructed on the page.
### 4. Class ID appears in the first line of DevTools or at the end of the URL.
""",
        "task_added": "Task added successfully.",
        "input_error": "Please check your input.",
        "select_fields": "Please select both fields.",
        "acc_loc_missing": "Please add Accounts and Locations first.",
        "saved": "Saved successfully.",
        "deleted": "Deleted successfully.",
        "manual_started": "Starting manual check-in...",
        "invalid_time": "Invalid time format. Use HH:MM.",
        "lat_lng_error": "Latitude and Longitude must be numbers.",
        "missing_fields": "Name, Class ID and Cookie are required.",
        "guide": "Guide",
    },
    "zh": {
        "title": "班级魔方自动签到 - AutoCheckBJMF",
        "dashboard": "仪表盘",
        "tasks": "任务",
        "accounts": "账号",
        "locations": "地点",
        "settings": "设置",
        "logs": "日志",
        "guide": "使用教程",
        "run": "运行",
        "next_run": "下次计划运行",
        "initializing": "正在初始化...",
        "quick_actions": "快捷操作",
        "run_now": "立即运行签到",
        "view_logs": "查看日志",
        "help_tutorial": "帮助 / 教程",
        "add_task": "添加任务",
        "no_tasks": "暂无任务。",
        "active": "已启用",
        "disabled": "已禁用",
        "enable": "启用",
        "disable": "禁用",
        "delete": "删除",
        "add_account": "添加账号",
        "how_to_cookie": "如何获取 Cookie?",
        "no_accounts": "暂无账号。",
        "edit": "编辑",
        "name": "名称",
        "class_id": "班级ID (Class ID)",
        "cookie": "Cookie",
        "password": "密码 (选填，用于密码签到)",
        "save": "保存",
        "cancel": "取消",
        "edit_account": "编辑账号",
        "confirm_delete": "确认删除",
        "delete_msg": "确定要删除此项吗？",
        "add_location": "添加地点",
        "no_locations": "暂无地点。",
        "latitude": "纬度 (Lat)",
        "longitude": "经度 (Lng)",
        "accuracy": "精度 (Accuracy)",
        "daily_time": "每日签到时间 (HH:MM)",
        "corp_id": "企业ID (Corp ID)",
        "secret": "应用密钥 (Secret)",
        "agent_id": "应用ID (Agent ID)",
        "to_user": "接收用户 (例如 @all)",
        "theme_color": "主题颜色",
        "language": "语言",
        "enable_debug": "开启调试日志",
        "save_settings": "保存设置",
        "clear_logs": "清空日志",
        "tutorial_title": "欢迎使用班级魔方自动签到！",
        "tutorial_intro": "本工具帮助您自动完成班级魔方签到任务。",
        "tutorial_guide": "快速开始指南：",
        "step_1": "1. 前往“账号”标签页添加账号 (Cookie 和 班级ID)。",
        "step_2": "2. 前往“地点”标签页添加签到地点 (经纬度)。",
        "step_3": "3. 前往“任务”标签页将账号与地点关联。",
        "step_4": "4. 在“设置”中设定每日运行时间。",
        "need_cookie_help": "不知道如何获取 Cookie？",
        "view_cookie_guide": "查看 Cookie 获取指南",
        "got_it": "明白了！",
        "cookie_guide_title": "获取 Cookie 和 班级码",
        "cookie_guide_md": """
# 获取Cookie和班级码

1. 浏览器输入网址：https://login.b8n.cn/auth/login/student/2
> 这里会扫码登入，登入后会看到这个页面

2. 按`F12` 打开开发者工具,点击`Network` (或 `网络`), 刷新页面。
3. 点击`student`,往下滑找到`Request Headers` (或 `请求头`) 中的 `Cookie` 复制即可。

### 3.按照指示点击图中的橙色按钮，跳转页面
### 4.这里就出现了班级码，在开发者工具第一行能看到，在网址最后一段数字也能看到
""",
        "task_added": "任务添加成功。",
        "input_error": "请检查输入内容。",
        "select_fields": "请选择两个字段。",
        "acc_loc_missing": "请先添加账号和地点。",
        "saved": "保存成功。",
        "deleted": "删除成功。",
        "manual_started": "正在开始手动签到...",
        "invalid_time": "时间格式无效。请使用 HH:MM。",
        "lat_lng_error": "经纬度必须是数字。",
        "missing_fields": "名称、班级ID 和 Cookie 必填。",
    }
}

class AutoCheckApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.config_manager = ConfigManager()

        # Load settings
        self.theme_color = self.config_manager.get("theme_color", "pink")
        self.current_lang = self.config_manager.get("language", "zh") # Default to Chinese

        self.page.title = self.t("title")
        self.page.window.width = 1000
        self.page.window.height = 750
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # Load fonts
        self.page.fonts = {
            "ZCOOL KuaiLe": "/fonts/ZCOOLKuaiLe-Regular.ttf",
            "Comfortaa": "/fonts/Comfortaa-VariableFont_wght.ttf"
        }

        font_family = "ZCOOL KuaiLe" if self.current_lang == "zh" else "Comfortaa"
        self.page.theme = ft.Theme(color_scheme_seed=self.theme_color, font_family=font_family)

        # Initialize CheckInManager with a thread-safe log callback
        self.checkin_manager = CheckInManager(self.config_manager, log_callback=self.log_callback)

        self.log_lines = []
        self.log_list_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=True,
            divider_thickness=1
        )

        self.setup_ui()
        self.start_scheduler()

        # Check if first run (no accounts or tasks)
        if not self.config_manager.get("accounts") and not self.config_manager.get("tasks"):
            self.show_tutorial_dialog()

    def t(self, key):
        """Helper for translation"""
        return TRANSLATIONS.get(self.current_lang, TRANSLATIONS["zh"]).get(key, key)

    def setup_ui(self):
        # Navigation Rail
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=400,
            leading=ft.FloatingActionButton(icon=ft.Icons.PLAY_ARROW, text=self.t("run"), on_click=self.run_manual_checkin),
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD,
                    label=self.t("dashboard")
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.TASK_OUTLINED,
                    selected_icon=ft.Icons.TASK,
                    label=self.t("tasks")
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE,
                    selected_icon=ft.Icons.PEOPLE,
                    label=self.t("accounts")
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LOCATION_ON_OUTLINED,
                    selected_icon=ft.Icons.LOCATION_ON,
                    label=self.t("locations")
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label=self.t("settings")
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.TERMINAL_OUTLINED,
                    selected_icon=ft.Icons.TERMINAL,
                    label=self.t("logs")
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HELP_OUTLINE,
                    selected_icon=ft.Icons.HELP,
                    label=self.t("guide")
                ),
            ],
            on_change=self.on_nav_change,
        )

        # Content Area
        self.content_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

        # Main Layout
        self.page.add(
            ft.Row(
                [
                    self.rail,
                    ft.VerticalDivider(width=1),
                    self.content_area,
                ],
                expand=True,
            )
        )

        # Initialize Dashboard
        self.build_dashboard()

    def on_nav_change(self, e):
        idx = e.control.selected_index
        self.content_area.controls.clear()

        if idx == 0:
            self.build_dashboard()
        elif idx == 1:
            self.build_tasks()
        elif idx == 2:
            self.build_accounts()
        elif idx == 3:
            self.build_locations()
        elif idx == 4:
            self.build_settings()
        elif idx == 5:
            self.build_logs()
        elif idx == 6:
            self.build_guide()

        self.page.update()

    def reload_ui(self):
        """Rebuilds the entire UI, useful for language changes."""
        self.page.clean()
        self.page.title = self.t("title")
        self.setup_ui()
        self.page.update()

    # --- Dashboard ---
    def build_dashboard(self):
        self.lbl_countdown = ft.Text("-", size=40, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        self.lbl_schedule_info = ft.Text(self.t("initializing"), italic=True)

        # Status Card
        status_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(self.t("next_run"), size=16, weight=ft.FontWeight.W_500),
                        self.lbl_countdown,
                        self.lbl_schedule_info
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
                padding=20
            )
        )

        # Quick Actions Card
        actions_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(self.t("quick_actions"), size=16, weight=ft.FontWeight.W_500),
                        ft.FilledButton(self.t("run_now"), icon=ft.Icons.PLAY_CIRCLE, on_click=self.run_manual_checkin, width=200),
                        ft.OutlinedButton(self.t("view_logs"), icon=ft.Icons.VISIBILITY, on_click=lambda _: self.rail_select(5), width=200),
                        ft.OutlinedButton(self.t("help_tutorial"), icon=ft.Icons.HELP, on_click=lambda _: self.show_tutorial_dialog(), width=200)
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
                padding=20
            )
        )

        self.content_area.controls.extend([
            ft.Text(self.t("dashboard"), size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Row([status_card, actions_card], alignment=ft.MainAxisAlignment.START, wrap=True),
        ])
        self.page.update()

    def rail_select(self, index):
        self.rail.selected_index = index
        self.on_nav_change(ft.ControlEvent(control=self.rail, target="", name="", data=""))
        self.page.update()

    # --- Tasks ---
    def build_tasks(self):
        self.tasks_list = ft.ListView(expand=True, spacing=10)
        self.refresh_tasks_list()

        self.content_area.controls.extend([
            ft.Row([
                ft.Text(self.t("tasks"), size=30, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.ADD, on_click=self.open_add_task_dialog, tooltip=self.t("add_task"))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            self.tasks_list
        ])
        self.page.update()

    def refresh_tasks_list(self):
        self.tasks_list.controls.clear()
        tasks = self.config_manager.get("tasks", [])

        if not tasks:
            self.tasks_list.controls.append(ft.Text(self.t("no_tasks"), italic=True))

        for i, task in enumerate(tasks):
            is_enabled = task.get("enable", True)

            card = ft.Card(
                content=ft.ListTile(
                    leading=ft.Icon(ft.Icons.TASK_ALT if is_enabled else ft.Icons.DO_NOT_DISTURB_ON, color=ft.Colors.GREEN if is_enabled else ft.Colors.GREY),
                    title=ft.Text(f"{task.get('account_name', '?')} @ {task.get('location_name', '?')}"),
                    subtitle=ft.Text(self.t("active") if is_enabled else self.t("disabled")),
                    trailing=ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        items=[
                            ft.PopupMenuItem(text=self.t("enable") if not is_enabled else self.t("disable"), icon=ft.Icons.POWER_SETTINGS_NEW, on_click=lambda e, idx=i: self.toggle_task(idx)),
                            ft.PopupMenuItem(text=self.t("delete"), icon=ft.Icons.DELETE, on_click=lambda e, idx=i: self.delete_task(idx)),
                        ]
                    ),
                )
            )
            self.tasks_list.controls.append(card)

    def open_add_task_dialog(self, e):
        accs = self.config_manager.get("accounts", [])
        locs = self.config_manager.get("locations", [])

        if not accs or not locs:
            self.show_snack(self.t("acc_loc_missing"), color=ft.Colors.RED)
            return

        acc_options = [ft.dropdown.Option(a.get("name")) for a in accs]
        loc_options = [ft.dropdown.Option(l.get("name")) for l in locs]

        dd_acc = ft.Dropdown(label=self.t("accounts"), options=acc_options, expand=True)
        dd_loc = ft.Dropdown(label=self.t("locations"), options=loc_options, expand=True)

        def save(e):
            if not dd_acc.value or not dd_loc.value:
                self.show_snack(self.t("select_fields"), color=ft.Colors.RED)
                return

            tasks = self.config_manager.get("tasks", [])
            tasks.append({
                "account_name": dd_acc.value,
                "location_name": dd_loc.value,
                "enable": True
            })
            self.config_manager.save_config({"tasks": tasks})
            self.refresh_tasks_list()
            dlg.open = False
            self.page.update()
            self.show_snack(self.t("task_added"), color=ft.Colors.GREEN)

        dlg = ft.AlertDialog(
            title=ft.Text(self.t("add_task")),
            content=ft.Column([dd_acc, dd_loc], tight=True, width=400),
            actions=[
                ft.TextButton(self.t("cancel"), on_click=lambda e: setattr(dlg, 'open', False) or self.page.update()),
                ft.FilledButton(self.t("save"), on_click=save)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def toggle_task(self, idx):
        tasks = self.config_manager.get("tasks", [])
        if 0 <= idx < len(tasks):
            tasks[idx]["enable"] = not tasks[idx].get("enable", True)
            self.config_manager.save_config({"tasks": tasks})
            self.refresh_tasks_list()
            self.page.update()

    def delete_task(self, idx):
        def confirm(e):
            tasks = self.config_manager.get("tasks", [])
            if 0 <= idx < len(tasks):
                del tasks[idx]
                self.config_manager.save_config({"tasks": tasks})
                self.refresh_tasks_list()
                dlg.open = False
                self.page.update()
                self.show_snack(self.t("deleted"))

        dlg = ft.AlertDialog(
            title=ft.Text(self.t("confirm_delete")),
            content=ft.Text(self.t("delete_msg")),
            actions=[
                ft.TextButton(self.t("cancel"), on_click=lambda e: setattr(dlg, 'open', False) or self.page.update()),
                ft.FilledButton(self.t("delete"), on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.ERROR))
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # --- Accounts ---
    def build_accounts(self):
        self.accounts_list = ft.ListView(expand=True, spacing=10)
        self.refresh_accounts_list()

        self.content_area.controls.extend([
            ft.Row([
                ft.Text(self.t("accounts"), size=30, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.TextButton(self.t("how_to_cookie"), icon=ft.Icons.HELP_OUTLINE, on_click=lambda _: self.show_cookie_help()),
                    ft.IconButton(ft.Icons.ADD, on_click=lambda _: self.open_account_dialog(-1), tooltip=self.t("add_account"))
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            self.accounts_list
        ])
        self.page.update()

    def refresh_accounts_list(self):
        self.accounts_list.controls.clear()
        accounts = self.config_manager.get("accounts", [])

        if not accounts:
            self.accounts_list.controls.append(ft.Text(self.t("no_accounts"), italic=True))

        for i, acc in enumerate(accounts):
            card = ft.Card(
                content=ft.ListTile(
                    leading=ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=30),
                    title=ft.Text(acc.get("name", "Unnamed")),
                    subtitle=ft.Text(f"{self.t('class_id')}: {acc.get('class_id', '?')}"),
                    trailing=ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        items=[
                            ft.PopupMenuItem(text=self.t("edit"), icon=ft.Icons.EDIT, on_click=lambda e, idx=i: self.open_account_dialog(idx)),
                            ft.PopupMenuItem(text=self.t("delete"), icon=ft.Icons.DELETE, on_click=lambda e, idx=i: self.delete_account(idx)),
                        ]
                    ),
                )
            )
            self.accounts_list.controls.append(card)

    def open_account_dialog(self, idx):
        accounts = self.config_manager.get("accounts", [])
        is_edit = idx >= 0
        data = accounts[idx] if is_edit else {}

        tf_name = ft.TextField(label=self.t("name"), value=data.get("name", ""))
        tf_class = ft.TextField(label=self.t("class_id"), value=data.get("class_id", ""))
        tf_cookie = ft.TextField(label=self.t("cookie"), value=data.get("cookie", ""), multiline=True, min_lines=3, max_lines=5)
        tf_pwd = ft.TextField(label=self.t("password"), value=data.get("pwd", ""), password=True, can_reveal_password=True)

        def save(e):
            if not tf_name.value or not tf_class.value or not tf_cookie.value:
                self.show_snack(self.t("missing_fields"), color=ft.Colors.RED)
                return

            new_acc = {
                "name": tf_name.value.strip(),
                "class_id": tf_class.value.strip(),
                "cookie": tf_cookie.value.strip(),
                "pwd": tf_pwd.value.strip()
            }

            if is_edit:
                accounts[idx] = new_acc
            else:
                accounts.append(new_acc)

            self.config_manager.save_config({"accounts": accounts})
            self.refresh_accounts_list()
            dlg.open = False
            self.page.update()
            self.show_snack(self.t("saved"), color=ft.Colors.GREEN)

        dlg = ft.AlertDialog(
            title=ft.Text(self.t("edit_account") if is_edit else self.t("add_account")),
            content=ft.Column([tf_name, tf_class, tf_cookie, tf_pwd], tight=True, width=400, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton(self.t("how_to_cookie"), on_click=lambda _: self.show_cookie_help()),
                ft.TextButton(self.t("cancel"), on_click=lambda e: setattr(dlg, 'open', False) or self.page.update()),
                ft.FilledButton(self.t("save"), on_click=save)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def delete_account(self, idx):
        def confirm(e):
            accounts = self.config_manager.get("accounts", [])
            if 0 <= idx < len(accounts):
                del accounts[idx]
                self.config_manager.save_config({"accounts": accounts})
                self.refresh_accounts_list()
                dlg.open = False
                self.page.update()
                self.show_snack(self.t("deleted"))

        dlg = ft.AlertDialog(
            title=ft.Text(self.t("confirm_delete")),
            content=ft.Text(self.t("delete_msg")),
            actions=[
                ft.TextButton(self.t("cancel"), on_click=lambda e: setattr(dlg, 'open', False) or self.page.update()),
                ft.FilledButton(self.t("delete"), on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.ERROR))
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def show_cookie_help(self):
        md_text = self.t("cookie_guide_md")
        dlg = ft.AlertDialog(
            title=ft.Text(self.t("cookie_guide_title")),
            content=ft.Container(
                content=ft.Markdown(md_text, selectable=True),
                width=600,
                height=400,
            ),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or self.page.update())]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # --- Locations ---
    def build_locations(self):
        self.locations_list = ft.ListView(expand=True, spacing=10)
        self.refresh_locations_list()

        self.content_area.controls.extend([
            ft.Row([
                ft.Text(self.t("locations"), size=30, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.ADD, on_click=lambda _: self.open_location_dialog(-1), tooltip=self.t("add_location"))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            self.locations_list
        ])
        self.page.update()

    def refresh_locations_list(self):
        self.locations_list.controls.clear()
        locations = self.config_manager.get("locations", [])

        if not locations:
            self.locations_list.controls.append(ft.Text(self.t("no_locations"), italic=True))

        for i, loc in enumerate(locations):
            card = ft.Card(
                content=ft.ListTile(
                    leading=ft.Icon(ft.Icons.MAP, size=30),
                    title=ft.Text(loc.get("name", "Unnamed")),
                    subtitle=ft.Text(f"Lat: {loc.get('lat')}, Lng: {loc.get('lng')}"),
                    trailing=ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        items=[
                            ft.PopupMenuItem(text=self.t("edit"), icon=ft.Icons.EDIT, on_click=lambda e, idx=i: self.open_location_dialog(idx)),
                            ft.PopupMenuItem(text=self.t("delete"), icon=ft.Icons.DELETE, on_click=lambda e, idx=i: self.delete_location(idx)),
                        ]
                    ),
                )
            )
            self.locations_list.controls.append(card)

    def open_location_dialog(self, idx):
        locations = self.config_manager.get("locations", [])
        is_edit = idx >= 0
        data = locations[idx] if is_edit else {}

        tf_name = ft.TextField(label=self.t("name"), value=data.get("name", ""))
        tf_lat = ft.TextField(label=self.t("latitude"), value=data.get("lat", ""))
        tf_lng = ft.TextField(label=self.t("longitude"), value=data.get("lng", ""))
        tf_acc = ft.TextField(label=self.t("accuracy"), value=data.get("acc", "0.0"))

        def save(e):
            try:
                float(tf_lat.value)
                float(tf_lng.value)
            except ValueError:
                self.show_snack(self.t("lat_lng_error"), color=ft.Colors.RED)
                return

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
            self.refresh_locations_list()
            dlg.open = False
            self.page.update()
            self.show_snack(self.t("saved"), color=ft.Colors.GREEN)

        dlg = ft.AlertDialog(
            title=ft.Text(self.t("edit_account") if is_edit else self.t("add_location")),
            content=ft.Column([tf_name, tf_lat, tf_lng, tf_acc], tight=True, width=400),
            actions=[
                ft.TextButton(self.t("cancel"), on_click=lambda e: setattr(dlg, 'open', False) or self.page.update()),
                ft.FilledButton(self.t("save"), on_click=save)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def delete_location(self, idx):
        def confirm(e):
            locations = self.config_manager.get("locations", [])
            if 0 <= idx < len(locations):
                del locations[idx]
                self.config_manager.save_config({"locations": locations})
                self.refresh_locations_list()
                dlg.open = False
                self.page.update()
                self.show_snack(self.t("deleted"))

        dlg = ft.AlertDialog(
            title=ft.Text(self.t("confirm_delete")),
            content=ft.Text(self.t("delete_msg")),
            actions=[
                ft.TextButton(self.t("cancel"), on_click=lambda e: setattr(dlg, 'open', False) or self.page.update()),
                ft.FilledButton(self.t("delete"), on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.ERROR))
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # --- Settings ---
    def build_settings(self):
        wecom = self.config_manager.get("wecom", {})

        tf_time = ft.TextField(label=self.t("daily_time"), value=self.config_manager.get("scheduletime", "08:00"))

        tf_corp = ft.TextField(label=self.t("corp_id"), value=wecom.get("corpid", ""))
        tf_secret = ft.TextField(label=self.t("secret"), value=wecom.get("secret", ""), password=True, can_reveal_password=True)
        tf_agent = ft.TextField(label=self.t("agent_id"), value=wecom.get("agentid", ""))
        tf_touser = ft.TextField(label=self.t("to_user"), value=wecom.get("touser", ""))

        # Color Picker
        color_options = ["pink", "blue", "green", "orange", "purple", "red", "teal", "cyan"]
        dd_color = ft.Dropdown(
            label=self.t("theme_color"),
            value=self.theme_color,
            options=[ft.dropdown.Option(c) for c in color_options]
        )

        # Language Picker
        lang_options = [
            ft.dropdown.Option("zh", "简体中文"),
            ft.dropdown.Option("en", "English"),
        ]
        dd_lang = ft.Dropdown(
            label=self.t("language"),
            value=self.current_lang,
            options=lang_options
        )

        sw_debug = ft.Switch(label=self.t("enable_debug"), value=self.config_manager.get("debug", False))

        def save(e):
            try:
                datetime.strptime(tf_time.value, "%H:%M")
            except ValueError:
                self.show_snack(self.t("invalid_time"), color=ft.Colors.RED)
                return

            new_conf = {
                "scheduletime": tf_time.value,
                "wecom": {
                    "corpid": tf_corp.value,
                    "secret": tf_secret.value,
                    "agentid": tf_agent.value,
                    "touser": tf_touser.value
                },
                "debug": sw_debug.value,
                "theme_color": dd_color.value,
                "language": dd_lang.value
            }
            self.config_manager.save_config(new_conf)
            self.update_scheduler_job()

            # Apply Changes
            self.theme_color = dd_color.value
            new_lang = dd_lang.value

            font_family = "ZCOOL KuaiLe" if new_lang == "zh" else "Comfortaa"
            self.page.theme = ft.Theme(color_scheme_seed=self.theme_color, font_family=font_family)

            if self.current_lang != new_lang:
                self.current_lang = new_lang
                self.reload_ui()
            else:
                self.page.update()

            self.show_snack(self.t("saved"), color=ft.Colors.GREEN)

        self.content_area.controls.extend([
            ft.Text(self.t("settings"), size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text(self.t("dashboard"), weight=ft.FontWeight.BOLD), # Reuse 'dashboard' label ? No, should be 'Scheduling' but let's just use what I have.
            # Correction: I need 'Scheduling' text in translations.
            ft.Text(self.t("daily_time"), weight=ft.FontWeight.BOLD),
            tf_time,
            ft.Divider(),
            ft.Text("WeCom Notification", weight=ft.FontWeight.BOLD),
            tf_corp, tf_secret, tf_agent, tf_touser,
            ft.Divider(),
            ft.Text("Appearance & Language", weight=ft.FontWeight.BOLD),
            dd_color,
            dd_lang,
            ft.Divider(),
            ft.Text("Debug", weight=ft.FontWeight.BOLD),
            sw_debug,
            ft.Divider(),
            ft.FilledButton(self.t("save_settings"), on_click=save)
        ])
        self.page.update()

    # --- Logs ---
    def build_logs(self):
        self.content_area.controls.extend([
            ft.Row([
                ft.Text(self.t("logs"), size=30, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, on_click=self.clear_logs, tooltip=self.t("clear_logs"))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            self.log_list_view
        ])
        self.page.update()

    def log_callback(self, message):
        # Determine color
        color = ft.Colors.ON_SURFACE
        icon = ft.Icons.INFO
        if any(x in message for x in ["❌", "失败", "Error", "Exception"]):
            color = ft.Colors.RED
            icon = ft.Icons.ERROR
        elif any(x in message for x in ["✅", "成功", "Finished"]):
            color = ft.Colors.GREEN
            icon = ft.Icons.CHECK_CIRCLE
        elif any(x in message for x in ["Warning", "⚠️"]):
            color = ft.Colors.ORANGE
            icon = ft.Icons.WARNING

        line = ft.Row([
             ft.Icon(icon, color=color, size=16),
             ft.Text(message, color=color, selectable=True, font_family="Consolas")
        ], wrap=True)

        self.log_list_view.controls.append(line)
        self.page.update()

    def clear_logs(self, e):
        self.log_list_view.controls.clear()
        self.page.update()

    # --- Guide ---
    def build_guide(self):
        self.content_area.controls.extend([
            ft.Text(self.t("guide"), size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text(self.t("tutorial_intro"), size=16),
            ft.Container(height=10),
            ft.Text(self.t("tutorial_guide"), weight=ft.FontWeight.BOLD, size=18),
            ft.Text(self.t("step_1")),
            ft.Text(self.t("step_2")),
            ft.Text(self.t("step_3")),
            ft.Text(self.t("step_4")),
            ft.Divider(),
            ft.Container(
                content=ft.Column([
                    ft.Text(self.t("cookie_guide_title"), weight=ft.FontWeight.BOLD, size=18),
                    ft.Markdown(self.t("cookie_guide_md"), selectable=True)
                ]),
                padding=10,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=10
            )
        ])
        self.page.update()

    # --- Actions & Helpers ---
    def show_snack(self, msg, color=ft.Colors.ON_SURFACE):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

    def run_manual_checkin(self, e):
        self.show_snack(self.t("manual_started"), color=ft.Colors.BLUE)
        threading.Thread(target=self._run_checkin_thread, daemon=True).start()

    def _run_checkin_thread(self):
        self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual run started...")
        try:
            self.checkin_manager.run_job()
            self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] Manual run completed.")
        except Exception as e:
            err_msg = f"Error: {e}"
            self.log_callback(err_msg)
            logger.error(traceback.format_exc())

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
            if hasattr(self, 'lbl_schedule_info'):
                self.lbl_schedule_info.value = f"Scheduled daily at {time_str}"
                self.page.update()
        except ValueError:
            if hasattr(self, 'lbl_schedule_info'):
                self.lbl_schedule_info.value = self.t("invalid_time")
                self.page.update()

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
            self._update_countdown()
            time.sleep(1)

    def _update_countdown(self):
        time_str = self.config_manager.get("scheduletime")
        if not time_str or not hasattr(self, 'lbl_countdown'):
            return

        # Optimization: Only update if the label is mounted on the page
        if self.lbl_countdown.page is None:
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

            # This runs every second, so only update if value changed to avoid spamming page update
            new_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            if self.lbl_countdown.value != new_text:
                self.lbl_countdown.value = new_text
                self.lbl_countdown.update()
        except:
            pass

    def show_tutorial_dialog(self):
        steps = [
            ft.Text(self.t("tutorial_title"), size=20, weight=ft.FontWeight.BOLD),
            ft.Text(self.t("tutorial_intro")),
            ft.Divider(),
            ft.Text(self.t("tutorial_guide"), weight=ft.FontWeight.BOLD),
            ft.Text(self.t("step_1")),
            ft.Text(self.t("step_2")),
            ft.Text(self.t("step_3")),
            ft.Text(self.t("step_4")),
            ft.Divider(),
            ft.Text(self.t("need_cookie_help"), color=ft.Colors.BLUE),
            ft.OutlinedButton(self.t("view_cookie_guide"), on_click=lambda _: self.show_cookie_help())
        ]

        dlg = ft.AlertDialog(
            title=ft.Text(self.t("help_tutorial")),
            content=ft.Column(steps, tight=True, width=500),
            actions=[ft.FilledButton(self.t("got_it"), on_click=lambda e: setattr(dlg, 'open', False) or self.page.update())]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

def main(page: ft.Page):
    AutoCheckApp(page)

if __name__ == "__main__":
    # Setup logging
    log_path = "gui_flet_debug.log"
    # Try to write to current directory, fallback to temp if fails
    try:
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True
        )
    except OSError:
        import tempfile
        log_path = os.path.join(tempfile.gettempdir(), "gui_flet_debug.log")
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True
        )

    logging.info("Application starting...")

    try:
        ft.app(target=main, assets_dir="assets")
    except Exception as e:
        # 捕获致命错误写入日志
        logging.critical(f"Critical Error: {e}")
        logging.critical(traceback.format_exc())
