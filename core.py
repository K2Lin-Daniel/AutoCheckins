import os
import sys
import json
import logging
import random
import re
import time
import requests
import schedule
from bs4 import BeautifulSoup
from datetime import datetime

"""
Core module for AutoCheckBJMF.

This module contains the core logic for the application, including configuration management,
API interaction, and task scheduling/execution.
"""

# ===========================
# 1. 日志与工具模块
# ===========================

def setup_logger(debug=False):
    """
    Configure logging for the application.

    Sets up a logger to output to the console with a specific format.

    Args:
        debug (bool): If True, sets logging level to DEBUG. Otherwise, INFO.

    Returns:
        logging.Logger: The configured logger instance.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger("BJMF_Auto")

logger = setup_logger()

def mask_str(s, show_len=4):
    """
    Mask sensitive strings for display in logs.

    Args:
        s (str): The string to mask.
        show_len (int): The number of characters to show at the start and end.

    Returns:
        str: The masked string (e.g., "abcd***wxyz").
    """
    if not s or len(s) <= show_len * 2:
        return "***"
    return f"{s[:show_len]}***{s[-show_len:]}"

# ===========================
# 2. 配置管理模块
# ===========================

class ConfigManager:
    """
    Manages application configuration.

    Loads configuration from 'config.json' and environment variables, prioritizing environment variables.
    Handles migration from older configuration formats.
    """
    def __init__(self, config_path=None):
        """
        Initialize the ConfigManager.

        Args:
            config_path (str, optional): Path to the configuration file.
                                         If None, automatically determines path based on execution environment (frozen or script).
        """
        if config_path:
            self.config_path = config_path
        else:
            # Determine path based on environment
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller executable
                base_dir = os.path.dirname(sys.executable)
            else:
                # Running as script
                base_dir = os.path.dirname(os.path.abspath(__file__))

            config_dir = os.path.join(base_dir, "config")
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            self.config_path = os.path.join(config_dir, "config.json")

        self.data = self._load_config()

        # Always save config to ensure defaults are present (e.g. scheduletime)
        # Check existence before saving for logging purposes
        is_new = not os.path.exists(self.config_path)
        self.save_config(self.data)
        logger.info(f"Configuration loaded from: {self.config_path}")
        if is_new:
            logger.info(f"Initialized default configuration at {self.config_path}")

    def _load_config(self):
        """
        Load configuration from file and environment variables.

        Merges defaults, file configuration, and environment variables.
        Also handles data migration from v1 and v2 config structures.

        Returns:
            dict: The loaded configuration dictionary.
        """
        # 默认配置
        config = {
            "locations": [], # List of {name, lat, lng, acc}
            "accounts": [],  # List of {name, cookie, class_id, pwd}
            "tasks": [],     # List of {account_name, location_name, enable}
            "scheduletime": "08:00",
            "wecom": {
                "corpid": "",
                "secret": "",
                "agentid": "",
                "touser": "@all"
            },
            # 兼容旧字段
            "pushplus": "",
            "class": "",
            "lat": "0.0",
            "lng": "0.0",
            "acc": "0.0",
            "cookie": [],
            "pwd": "",
            "users": [] # 兼容之前版本的多用户结构
        }

        # 1. 尝试从文件加载
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                logger.warning(f"配置文件读取失败: {e}，将使用默认值/环境变量")

        # 2. 尝试从环境变量加载
        env_map = {
            "ClassID": "class",
            "X": "lat",
            "Y": "lng",
            "ACC": "acc",
            "SearchTime": "scheduletime",
            "token": "pushplus",
            "PASSWORD": "pwd",
            "WECOM_CORPID": "wecom.corpid",
            "WECOM_SECRET": "wecom.secret",
            "WECOM_AGENTID": "wecom.agentid",
            "WECOM_TOUSER": "wecom.touser"
        }
        
        for env_key, conf_key in env_map.items():
            val = os.environ.get(env_key)
            if val:
                if "." in conf_key:
                    section, key = conf_key.split(".")
                    if section in config and isinstance(config[section], dict):
                        config[section][key] = val
                else:
                    config[conf_key] = val

        # 3. 特殊处理 Cookie
        env_cookie = os.environ.get("MyCookie")
        if env_cookie:
            cookies = [c.strip() for c in re.split(r'[&\n]', env_cookie) if c.strip()]
            config["cookie"] = cookies
        
        if isinstance(config["cookie"], str):
            config["cookie"] = [config["cookie"]]

        # 4. 迁移逻辑
        if not config["tasks"]:
            # 优先检查 users 列表 (v2结构)
            users_v2 = config.get("users", [])
            if users_v2:
                for idx, u in enumerate(users_v2):
                    loc_name = f"Location_{idx+1}"
                    acc_name = u.get("remark", f"User_{idx+1}")

                    # 添加地点
                    if not any(l['name'] == loc_name for l in config["locations"]):
                        config["locations"].append({
                            "name": loc_name,
                            "lat": u.get("lat", "0"),
                            "lng": u.get("lng", "0"),
                            "acc": u.get("acc", "0")
                        })

                    # 添加账号 (绑定 ClassID)
                    if not any(a['name'] == acc_name for a in config["accounts"]):
                        config["accounts"].append({
                            "name": acc_name,
                            "cookie": u.get("cookie", ""),
                            "class_id": u.get("class_id", ""),
                            "pwd": u.get("pwd", "")
                        })

                    # 添加任务
                    config["tasks"].append({
                        "account_name": acc_name,
                        "location_name": loc_name,
                        "enable": u.get("enable", True)
                    })
            else:
                # 检查 v1 结构 (扁平配置)
                cookies = config.get("cookie", [])
                class_id = config.get("class")
                if cookies and class_id:
                    # 确定默认地点
                    if config["locations"]:
                        def_loc_name = config["locations"][0]["name"]
                    else:
                        def_loc_name = "Default Location"
                        config["locations"].append({
                            "name": def_loc_name,
                            "lat": config.get("lat", "0.0"),
                            "lng": config.get("lng", "0.0"),
                            "acc": config.get("acc", "0.0")
                        })

                    # 创建账号和任务
                    for idx, c in enumerate(cookies):
                        acc_name = self._extract_username_static(c)
                        if acc_name == "User":
                             acc_name = f"User_{idx+1}"

                        if not any(a['name'] == acc_name for a in config["accounts"]):
                            config["accounts"].append({
                                "name": acc_name,
                                "cookie": c,
                                "class_id": class_id,
                                "pwd": config.get("pwd", "")
                            })

                        config["tasks"].append({
                            "account_name": acc_name,
                            "location_name": def_loc_name,
                            "enable": True
                        })

        return config

    def _extract_username_static(self, cookie):
        """
        Static helper to extract username from a cookie string.

        Args:
            cookie (str): The cookie string.

        Returns:
            str: The extracted username or "User" if not found.
        """
        match = re.search(r'username=([^;]+)', cookie)
        return match.group(1) if match else "User"

    def get(self, key, default=None):
        """
        Get a configuration value.

        Args:
            key (str): The configuration key to retrieve.
            default (Any, optional): The default value if the key is missing.

        Returns:
            Any: The configuration value or the default.
        """
        return self.data.get(key, default)

    def save_config(self, new_data):
        """
        Save configuration updates to the file.

        Args:
            new_data (dict): A dictionary of configuration keys and values to update.
        """
        self.data.update(new_data)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

# ===========================
# 3. 核心 API 交互模块
# ===========================

class BJMFClient:
    """
    Client for interacting with the Class Cube (BJMF) server.

    Handles HTTP requests, session management, and parsing server responses.
    """
    SERVER = "k8n.cn"
    # 模拟微信内置浏览器 UA
    UA = "Mozilla/5.0 (Linux; Android 12; PAL-AL00 Build/HUAWEIPAL-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 XWEB/1160065 MMWEBSDK/20231202 MMWEBID/1136 MicroMessenger/8.0.47.2560(0x28002F35) WeChat/arm64 Weixin NetType/4G Language/zh_CN ABI/arm64"

    def __init__(self, cookie, class_id):
        """
        Initialize the BJMFClient.

        Args:
            cookie (str): The user's authentication cookie.
            class_id (str): The class ID to check tasks for.
        """
        self.cookie = cookie
        self.class_id = class_id
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())
        # 尝试提取用户名用于日志显示
        self.username = self._extract_username(cookie)

    def _extract_username(self, cookie):
        """
        Extract the username from the cookie.

        Args:
            cookie (str): The cookie string.

        Returns:
            str: The extracted username or "Unknown".
        """
        match = re.search(r'username=([^;]+)', cookie)
        return match.group(1) if match else "Unknown"

    def _get_headers(self):
        """
        Generate HTTP headers for requests.

        Returns:
            dict: A dictionary of HTTP headers including User-Agent and Cookie.
        """
        return {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/wxpic,image/tpg,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "X-Requested-With": "com.tencent.mm",
            "Referer": f"http://{self.SERVER}/student/course/{self.class_id}",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh-SG;q=0.9,zh;q=0.8,en-SG;q=0.7,en-US;q=0.6,en;q=0.5",
            "Cookie": self.cookie,
        }

    def fetch_tasks(self):
        """
        Fetch all pending check-in task IDs.

        Scrapes the course page to find check-in cards that are not yet marked as "Signed".

        Returns:
            list: A list of task ID strings if successful.
            None: If the session/cookie is invalid.
            list: An empty list if no tasks are found or an error occurs.
        """
        url = f"http://{self.SERVER}/student/course/{self.class_id}/punchs"
        try:
            r = self.session.get(url, timeout=15)
            # 检查 Cookie 是否有效
            if "出错" in r.text or ("登录" in r.text and "输入密码" in r.text):
                logger.error(f"用户 [{self.username}] Cookie 已失效或需登录")
                return None # None 表示 Cookie 失效

            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.find_all("div", class_="card-body")
            
            valid_ids = []
            for card in cards:
                card_str = str(card)
                # 核心逻辑：如果包含“已签”，则跳过
                if "已签" in card_str:
                    continue
                
                # 提取 ID (兼容普通签到和密码签到)
                match = re.search(r'(punchcard|punch_pwd_frm)_(\d+)', card_str)
                if match:
                    valid_ids.append(match.group(2))
            
            return valid_ids
        except Exception as e:
            logger.error(f"用户 [{self.username}] 获取任务列表失败: {e}")
            return []

    def execute_sign(self, sign_id, lat, lng, acc, pwd=""):
        """
        Execute a single check-in request.

        Args:
            sign_id (str): The ID of the check-in task.
            lat (str/float): Latitude for the check-in.
            lng (str/float): Longitude for the check-in.
            acc (str/float): Accuracy of the location.
            pwd (str, optional): Password for password-protected check-ins. Defaults to "".

        Returns:
            str: The result message from the server (e.g., "Success", error message).
        """
        url = f"http://{self.SERVER}/student/punchs/course/{self.class_id}/{sign_id}"
        data = {
            "id": sign_id,
            "lat": lat,
            "lng": lng,
            "acc": acc,
            "res": "",
            "gps_addr": "",
            "pwd": pwd
        }
        try:
            r = self.session.post(url, data=data, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            h1 = soup.find("h1")
            return h1.text if h1 else "未知响应"
        except Exception as e:
            logger.error(f"签到请求异常: {e}")
            return str(e)

# ===========================
# 4. 任务调度与执行模块
# ===========================

class CheckInManager:
    """
    Manages the check-in process logic.

    Coordinates configuration, client execution, and notifications.
    """
    def __init__(self, config_manager, log_callback=None):
        """
        Initialize the CheckInManager.

        Args:
            config_manager (ConfigManager): The configuration manager instance.
            log_callback (callable, optional): A callback function for logging messages (e.g., for GUI updates).
        """
        self.cfg = config_manager
        self.log_callback = log_callback

    def _get_jittered_location(self, lat, lng, acc):
        """
        Get coordinates with random jitter added to simulate real GPS fluctuations.

        Args:
            lat (str/float): Base latitude.
            lng (str/float): Base longitude.
            acc (str/float): Accuracy.

        Returns:
            tuple: (jittered_lat, jittered_lng, acc)
        """
        try:
            base_lat = float(lat)
            base_lng = float(lng)
            # 随机抖动范围 (约 10-20米)
            offset = random.uniform(-0.00015, 0.00015)
            return base_lat + offset, base_lng + offset, acc
        except ValueError:
            logger.critical("坐标配置错误，请检查 lat/lng 是否为数字")
            return 0, 0, 0

    def _push_notify(self, content):
        """
        Send a notification via WeCom (Enterprise WeChat) or PushPlus.

        Args:
            content (str): The message content to send.
        """
        wecom = self.cfg.get("wecom", {})
        corpid = wecom.get("corpid")
        secret = wecom.get("secret")
        agentid = wecom.get("agentid")

        if not corpid or not secret or not agentid:
            # 尝试回退到 pushplus (兼容旧配置)
            token = self.cfg.get("pushplus")
            if token:
                self._push_pushplus(token, content)
            return

        try:
            # 1. 获取 Access Token
            token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={secret}"
            r = requests.get(token_url, timeout=10)
            token_data = r.json()

            if token_data.get("errcode") != 0:
                logger.error(f"企业微信 AccessToken 获取失败: {token_data}")
                return

            access_token = token_data.get("access_token")

            # 2. 发送消息
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            payload = {
                "touser": wecom.get("touser", "@all"),
                "msgtype": "text",
                "agentid": agentid,
                "text": {
                    "content": f"【班级魔法签到通知】\n{content}"
                },
                "safe": 0
            }

            r_send = requests.post(send_url, json=payload, timeout=10)
            res = r_send.json()
            if res.get("errcode") == 0:
                logger.info("企业微信推送成功")
            else:
                logger.warning(f"企业微信推送失败: {res}")

        except Exception as e:
            logger.warning(f"推送异常: {e}")

    def _push_pushplus(self, token, content):
        """
        Send a notification via PushPlus (fallback method).

        Args:
            token (str): The PushPlus token.
            content (str): The message content.
        """
        url = 'http://www.pushplus.plus/send'
        data = {
            "token": token,
            "title": "班级魔法签到通知",
            "content": content
        }
        try:
            requests.post(url, json=data, timeout=5)
            logger.info("PushPlus 推送已发送")
        except Exception as e:
            logger.warning(f"PushPlus 推送失败: {e}")

    def log(self, msg):
        """
        Log a message to the logger and the optional callback.

        Args:
            msg (str): The message to log.
        """
        logger.info(msg)
        if self.log_callback:
            self.log_callback(msg)

    def run_job(self):
        """
        Adapter method for job execution, equivalent to calling run_with_retries.
        """
        self.run_with_retries()

    def run_check_flow(self):
        """
        Execute a complete check-in flow for all enabled tasks.

        Iterates through tasks, fetches pending check-ins, performs them,
        and sends notifications.

        Returns:
            bool: True if any task failed and needs retry, False otherwise.
        """
        self.log("--- 开始执行签到任务 ---")

        tasks = self.cfg.get("tasks", [])
        locations = self.cfg.get("locations", [])
        accounts = self.cfg.get("accounts", [])

        if not tasks:
            self.log("任务列表为空，跳过任务")
            return

        push_messages = []
        needs_retry = False

        # 将 list 转为 dict 方便查找
        loc_map = {l["name"]: l for l in locations}
        acc_map = {a["name"]: a for a in accounts}

        # Cache clients to avoid recreating sessions for the same account
        # Key: (cookie, class_id) -> client instance
        client_cache = {}

        for task in tasks:
            if not task.get("enable", True):
                continue

            acc_name = task.get("account_name")
            loc_name = task.get("location_name")

            account = acc_map.get(acc_name)
            location = loc_map.get(loc_name)

            if not account or not location:
                self.log(f"任务无效: 找不到账号 [{acc_name}] 或 地点 [{loc_name}]")
                continue

            cookie = account.get("cookie")
            class_id = account.get("class_id")

            if not cookie or not class_id:
                self.log(f"账号 [{acc_name}] 配置不完整 (缺少Cookie或ClassID)，跳过")
                continue

            # Use cached client or create new one
            client_key = (cookie, class_id)
            if client_key not in client_cache:
                client_cache[client_key] = BJMFClient(cookie, class_id)

            client = client_cache[client_key]

            self.log(f"正在执行任务: [{acc_name}] @ [{loc_name}]")

            pending_tasks = client.fetch_tasks()
            
            if pending_tasks is None:
                # Avoid duplicate error messages for the same account in one run
                msg = f"任务 {acc_name}: Cookie 失效 ❌"
                if msg not in push_messages:
                    push_messages.append(msg)
                continue
            
            if not pending_tasks:
                self.log(f"账号 [{acc_name}] 无需签到")
                continue

            # 开始签到
            lat = location.get("lat", "0")
            lng = location.get("lng", "0")
            acc = location.get("acc", "0")
            pwd = account.get("pwd", "")

            r_lat, r_lng, r_acc = self._get_jittered_location(lat, lng, acc)

            for task_id in pending_tasks:
                result = client.execute_sign(task_id, r_lat, r_lng, r_acc, pwd)
                self.log(f"任务 [{acc_name}] 签到ID [{task_id}] 结果: {result}")
                
                status_icon = "✅" if "成功" in result else "❌"
                push_messages.append(f"任务 {acc_name} @ {loc_name}: {result} {status_icon}")
                
                if "成功" not in result:
                    needs_retry = True

        # 发送推送
        if push_messages:
            self._push_notify("\n".join(push_messages))
        
        self.log("--- 本次任务结束 ---")
        return needs_retry

    def run_with_retries(self):
        """
        Run the check-in flow with a retry mechanism.

        If the initial run has failures, it will retry after 5 and 15 minutes.
        """
        # 初次运行
        failed = self.run_check_flow()
        
        # 如果有失败，进行有限次重试
        if failed:
            retries = [5, 15] # 分别在 5分钟 和 15分钟 后重试
            for wait_min in retries:
                self.log(f"检测到失败任务，将在 {wait_min} 分钟后重试...")
                time.sleep(wait_min * 60)
                failed = self.run_check_flow()
                if not failed:
                    break
            if failed:
                self.log("多次重试后仍有任务失败，放弃。")

# ===========================
# 5. 程序入口
# ===========================

if __name__ == "__main__":
    # 初始化配置
    config = ConfigManager()
    manager = CheckInManager(config)
    
    # 检查是否在 GitHub Actions 或其他 CI 环境
    is_ci = os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI")
    
    if is_ci:
        logger.info("检测到 CI 环境，运行一次后退出")
        manager.run_with_retries()
    else:
        schedule_time = config.get("scheduletime", "08:00")
        logger.info(f"本地模式启动，定时任务已设定为: {schedule_time}")
        
        # 立即运行一次测试
        # manager.run_with_retries()
        
        schedule.every().day.at(schedule_time).do(manager.run_with_retries)
        
        while True:
            schedule.run_pending()
            time.sleep(10)