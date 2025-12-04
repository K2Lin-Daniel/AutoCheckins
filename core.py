import os
import json
import logging
import random
import re
import time
import requests
import schedule
from bs4 import BeautifulSoup
from datetime import datetime

# ===========================
# 1. 日志与工具模块
# ===========================

def setup_logger():
    """配置日志，输出到控制台，并支持简单的脱敏处理"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger("BJMF_Auto")

logger = setup_logger()

def mask_str(s, show_len=4):
    """对敏感字符串进行脱敏处理"""
    if not s or len(s) <= show_len * 2:
        return "***"
    return f"{s[:show_len]}***{s[-show_len:]}"

# ===========================
# 2. 配置管理模块
# ===========================

class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.data = self._load_config()

    def _load_config(self):
        # 默认配置
        config = {
            "class": "",
            "lat": "0.0",
            "lng": "0.0",
            "acc": "0.0",
            "cookie": [],
            "scheduletime": "08:00",
            "pushplus": "",
            "pwd": "" # 预留密码字段
        }

        # 1. 尝试从文件加载
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                logger.warning(f"配置文件读取失败: {e}，将使用默认值/环境变量")

        # 2. 尝试从环境变量加载 (优先级更高，覆盖文件配置)
        env_map = {
            "ClassID": "class",
            "X": "lat",
            "Y": "lng",
            "ACC": "acc",
            "SearchTime": "scheduletime",
            "token": "pushplus",
            "PASSWORD": "pwd"
        }
        
        for env_key, conf_key in env_map.items():
            val = os.environ.get(env_key)
            if val:
                config[conf_key] = val

        # 3. 特殊处理 Cookie (支持多账号，以 & 或换行分隔)
        env_cookie = os.environ.get("MyCookie")
        if env_cookie:
            # 分割并去空
            cookies = [c.strip() for c in re.split(r'[&\n]', env_cookie) if c.strip()]
            config["cookie"] = cookies
        
        # 确保 cookie 是列表
        if isinstance(config["cookie"], str):
            config["cookie"] = [config["cookie"]]

        return config

    def get(self, key, default=None):
        return self.data.get(key, default)

# ===========================
# 3. 核心 API 交互模块
# ===========================

class BJMFClient:
    """负责与服务器进行 HTTP 交互，不包含业务调度逻辑"""
    SERVER = "k8n.cn"
    # 模拟微信内置浏览器 UA
    UA = "Mozilla/5.0 (Linux; Android 12; PAL-AL00 Build/HUAWEIPAL-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 XWEB/1160065 MMWEBSDK/20231202 MMWEBID/1136 MicroMessenger/8.0.47.2560(0x28002F35) WeChat/arm64 Weixin NetType/4G Language/zh_CN ABI/arm64"

    def __init__(self, cookie, class_id):
        self.cookie = cookie
        self.class_id = class_id
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())
        # 尝试提取用户名用于日志显示
        self.username = self._extract_username(cookie)

    def _extract_username(self, cookie):
        match = re.search(r'username=([^;]+)', cookie)
        return match.group(1) if match else "Unknown"

    def _get_headers(self):
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
        """获取所有未签到的任务ID"""
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
        """执行单个签到请求"""
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

class AutoCheckJob:
    def __init__(self, config_manager):
        self.cfg = config_manager

    def _get_jittered_location(self):
        """获取带随机抖动的坐标"""
        try:
            base_lat = float(self.cfg.get("lat"))
            base_lng = float(self.cfg.get("lng"))
            # 随机抖动范围 (约 10-20米)
            offset = random.uniform(-0.00015, 0.00015)
            return base_lat + offset, base_lng + offset, self.cfg.get("acc")
        except ValueError:
            logger.critical("坐标配置错误，请检查 lat/lng 是否为数字")
            return 0, 0, 0

    def _push_notify(self, content):
        token = self.cfg.get("pushplus")
        if not token:
            return
        url = 'http://www.pushplus.plus/send'
        data = {
            "token": token,
            "title": "班级魔法签到通知",
            "content": content
        }
        try:
            requests.post(url, json=data, timeout=5)
            logger.info("推送通知已发送")
        except Exception as e:
            logger.warning(f"推送失败: {e}")

    def run_check_flow(self):
        """执行一次完整的检查流程（遍历所有用户）"""
        logger.info("--- 开始执行签到任务 ---")
        cookies = self.cfg.get("cookie", [])
        class_id = self.cfg.get("class")
        pwd = self.cfg.get("pwd", "")

        if not cookies or not class_id:
            logger.warning("未配置 Cookie 或 ClassID，跳过任务")
            return

        push_messages = []
        needs_retry = False

        for i, cookie in enumerate(cookies):
            client = BJMFClient(cookie, class_id)
            logger.info(f"正在检查用户 [{client.username}] ...")

            tasks = client.fetch_tasks()
            
            if tasks is None:
                push_messages.append(f"用户 {client.username}: Cookie 失效 ❌")
                continue
            
            if not tasks:
                logger.info(f"用户 [{client.username}] 无需签到")
                continue

            # 开始签到
            lat, lng, acc = self._get_jittered_location()
            for task_id in tasks:
                result = client.execute_sign(task_id, lat, lng, acc, pwd)
                logger.info(f"用户 [{client.username}] 任务 [{task_id}] 结果: {result}")
                
                status_icon = "✅" if "成功" in result else "❌"
                push_messages.append(f"用户 {client.username}: {result} {status_icon}")
                
                if "成功" not in result:
                    needs_retry = True

        # 发送推送
        if push_messages:
            self._push_notify("\n".join(push_messages))
        
        logger.info("--- 本次任务结束 ---")
        return needs_retry

    def run_with_retries(self):
        """带重试机制的运行入口"""
        # 初次运行
        failed = self.run_check_flow()
        
        # 如果有失败，进行有限次重试
        if failed:
            retries = [5, 15] # 分别在 5分钟 和 15分钟 后重试
            for wait_min in retries:
                logger.info(f"检测到失败任务，将在 {wait_min} 分钟后重试...")
                time.sleep(wait_min * 60)
                failed = self.run_check_flow()
                if not failed:
                    break
            if failed:
                logger.error("多次重试后仍有任务失败，放弃。")

# ===========================
# 5. 程序入口
# ===========================

if __name__ == "__main__":
    # 初始化配置
    config = ConfigManager()
    job = AutoCheckJob(config)
    
    # 检查是否在 GitHub Actions 或其他 CI 环境
    is_ci = os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI")
    
    if is_ci:
        logger.info("检测到 CI 环境，运行一次后退出")
        job.run_with_retries()
    else:
        schedule_time = config.get("scheduletime", "08:00")
        logger.info(f"本地模式启动，定时任务已设定为: {schedule_time}")
        
        # 立即运行一次测试
        # job.run_with_retries() 
        
        schedule.every().day.at(schedule_time).do(job.run_with_retries)
        
        while True:
            schedule.run_pending()
            time.sleep(10)