import os
import json
import logging
import random
import re
import time
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import schedule

# Setup logging
logger = logging.getLogger("AutoCheckBJMF")

def setup_logger(debug_mode=False):
    logger.handlers = []
    logger.setLevel(logging.INFO)

    if debug_mode:
        # Create file handler
        file_handler = logging.FileHandler('AutoCheckBJMF.log', encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info("Debug mode enabled")

def print_log(type, message, debug_mode=False):
    if debug_mode:
        if type == "info":
            logger.info(message)
        elif type == "warning":
            logger.warning(message)
        elif type == "error":
            logger.error(message)
        elif type == "critical":
            logger.critical(message)
        else:
            logger.info(message)

class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.data = self.load_config()

    def load_config(self):
        default_config = {
            "class": "",
            "lat": "",
            "lng": "",
            "acc": "",
            "time": 0,
            "cookie": [],
            "scheduletime": "",
            "pushplus": "",
            "debug": False,
            "configLock": False
        }

        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as file:
                json.dump(default_config, file, indent=4)
            return default_config

        try:
            # First try loading from file
            file_data = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as file:
                    file_data = json.load(file)

            # Check for environment variables (override/fill defaults)
            # Mappings: Env Var -> Config Key
            env_map = {
                "ClassID": "class",
                "X": "lat",
                "Y": "lng",
                "ACC": "acc",
                "SearchTime": "scheduletime",
                "token": "pushplus",
                # "MyCookie" handled specially below
            }

            env_data = {}
            for env_key, config_key in env_map.items():
                if os.environ.get(env_key):
                    env_data[config_key] = os.environ.get(env_key)

            if os.environ.get("MyCookie"):
                # workflow might pass single string or list-like string?
                # Assuming single string or list; we treat it as adding to list
                c = os.environ.get("MyCookie")
                if c:
                    env_data["cookie"] = [c]

            # Determine final data source priority: Env > File > Default
            # However, if config.json exists and has valid data, usually we prefer that?
            # But the use case here is GitHub Actions injecting secrets.
            # If Env vars are present, they should likely take precedence or at least fill in gaps.
            # Given the workflow runs on fresh VM, config.json won't exist anyway.
            # So mixing them safely:

            data = default_config.copy()
            data.update(file_data) # Load from file
            data.update(env_data)  # Override with Env

            # Ensure cookies is a list
            if isinstance(data.get("cookie"), str):
                if data["cookie"]:
                    data["cookie"] = [data["cookie"]]
                else:
                    data["cookie"] = []

            # If we have critical data from Env, we should consider it "locked" to avoid interactive prompt in main.py
            # Critical fields: class
            if env_data.get("class"):
                data["configLock"] = True

            return data

        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def save_config(self, data):
        self.data = data
        with open(self.config_path, "w") as file:
            json.dump(data, file, indent=4)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

class CheckInManager:
    def __init__(self, config_manager, log_callback=None):
        self.config = config_manager
        self.log_callback = log_callback

    def log(self, message):
        print(message)
        if self.log_callback:
            self.log_callback(message)

    def modify_decimal_part(self, num):
        offset = random.uniform(-0.00015, 0.00015)
        return float(num) + offset

    def send_push(self, token, content):
        url = 'http://www.pushplus.plus/send?token=' + token + '&title=' + "班级魔法自动签到任务" + '&content=' + content
        try:
            requests.get(url, timeout=10)
        except Exception as e:
            self.log(f"Push failed: {e}")

    def qiandao(self, cookies=None):
        if cookies is None:
            cookies = self.config.get("cookie", [])

        class_id = self.config.get("class")
        x = self.config.get("lat")
        y = self.config.get("lng")
        acc = self.config.get("acc")
        pushtoken = self.config.get("pushplus")
        debug = self.config.get("debug")

        error_cookie = []
        null_cookie = 0

        if not cookies:
             self.log("No cookies to process.")
             return [], 0

        url = 'http://k8n.cn/student/course/' + str(class_id) + '/punchs'

        for uid, only_cookie in enumerate(cookies):
             # Extract username for display
            pattern = r'username=[^;]+'
            result = re.search(pattern, only_cookie)
            username_string = " <%s>" % result.group(0).split("=")[1] if result else ""

            self.log(f"User {uid+1}{username_string} checking...")

            pattern = r'remember_student_[0-9a-fA-F]+=[^;]+'
            result = re.search(pattern, only_cookie)

            if result:
                extracted_string = result.group(0)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 9; AKT-AK47 Build/USER-AK47; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 XWEB/1160065 MMWEBSDK/20231202 MMWEBID/1136 MicroMessenger/8.0.47.2560(0x28002F35) WeChat/arm64 Weixin NetType/4G Language/zh_CN ABI/arm64',
                    'Cookie': extracted_string,
                    'Referer': 'http://k8n.cn/student/course/' + str(class_id)
                }

                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if "出错" in response.text or "登录" in response.text and "输入密码" in response.text:
                         # Simple check, improved via soup below
                         pass

                    soup = BeautifulSoup(response.text, 'html.parser')
                    title_tag = soup.find('title')

                    if title_tag and "出错" not in title_tag.text:
                        pattern = re.compile(r'punch_gps\((\d+)\)')
                        matches = pattern.findall(response.text)
                        pattern2 = re.compile(r'punchcard_(\d+)')
                        matches2 = pattern2.findall(response.text)
                        matches.extend(matches2)

                        if matches:
                            for match in matches:
                                url1 = "http://k8n.cn/student/punchs/course/" + str(class_id) + "/" + match
                                newX = self.modify_decimal_part(x)
                                newY = self.modify_decimal_part(y)
                                payload = {
                                    'id': match,
                                    'lat': newX,
                                    'lng': newY,
                                    'acc': acc,
                                    'res': '',
                                    'gps_addr': ''
                                }

                                try:
                                    response = requests.post(url1, headers=headers, data=payload, timeout=10)
                                    self.log(f"Sent: ID[{match}] Loc[{newX},{newY}]")

                                    if response.status_code == 200:
                                        soup_response = BeautifulSoup(response.text, 'html.parser')
                                        div_tag = soup_response.find('div', id='title')
                                        if div_tag:
                                            h1_text = div_tag.text
                                            self.log(f"Result: {h1_text}")
                                            if pushtoken and h1_text == "签到成功":
                                                self.send_push(pushtoken, h1_text)
                                        else:
                                            self.log("Error parsing response.")
                                    else:
                                        self.log(f"Failed: {response.status_code}")
                                        error_cookie.append(only_cookie)
                                except Exception as e:
                                    self.log(f"POST Error: {e}")
                                    error_cookie.append(only_cookie)
                        else:
                            self.log("No active check-in.")
                    else:
                        self.log("Login failed or session expired.")
                        error_cookie.append(only_cookie)
                except Exception as e:
                    self.log(f"GET Error: {e}")
                    error_cookie.append(only_cookie)
            else:
                null_cookie += 1
                self.log("Invalid cookie format.")

        return error_cookie, null_cookie

    def run_job(self):
        self.log(f"\n--- Starting Job at {datetime.now()} ---")
        cookies = self.config.get("cookie", [])
        error_cookie, null_cookie = self.qiandao(cookies)

        if len(error_cookie) > 0:
            self.log("Retry in 5 mins...")
            time.sleep(300)
            error_cookie, _ = self.qiandao(error_cookie)
            if len(error_cookie) > 0:
                self.log("Retry in 15 mins...")
                time.sleep(900)
                error_cookie, _ = self.qiandao(error_cookie)
                if len(error_cookie) > 0:
                    self.log("Some cookies permanently failed.")

        self.log("--- Job Finished ---")
