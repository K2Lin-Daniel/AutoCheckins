from core import ConfigManager, CheckInManager, setup_logger
import schedule
import time
import os

"""
CLI entry point for AutoCheckBJMF.

This module provides a command-line interface for running the check-in process.
It handles initial configuration for new users and executes the scheduled or manual check-in tasks.
"""

def main():
    """
    Main entry point for the CLI application.

    Checks for existing configuration. If not found (and configLock is False),
    it prompts the user for initial setup (single account, single location).
    Then it initializes the CheckInManager and either runs a one-time check-in
    or starts the scheduler based on the configuration.
    """
    print("----------提醒----------")
    print("项目地址：https://github.com/JasonYANG170/AutoCheckBJMF")
    print("请查看教程以获取Cookie和班级ID")

    config = ConfigManager()
    print("config.json文件位置：", config.config_path)

    # CLI setup if not locked and no tasks configured
    if not config.get("configLock") and not config.get("tasks"):
        print("----------首次运行配置初始化----------")
        print("注意：新版支持多账号多地点，CLI 仅提供最基础的单账号单地点配置。")
        print("建议使用 GUI (gui.py) 进行更复杂的管理。")

        print("\n=== 步骤 1: 账号配置 ===")
        class_id = input("请输入默认班级ID：")
        cookie = input("请输入 Cookie：")
        acc_name = "Default Account"

        print("\n=== 步骤 2: 地点配置 ===")
        print("☆输入的经纬度格式为x.x，请输入至少8位小数用于定位微偏移，不满8位用0替补！")
        print("☆腾讯坐标拾取工具：https://lbs.qq.com/getPoint/")
        lat = input("请输入纬度(X)：")
        lng = input("请输入经度(Y)：")
        acc = input("请输入海拔(ACC, 可选，默认0)：") or "0"
        loc_name = "Default Location"

        print("\n=== 步骤 3: 其他配置 ===")
        scheduletime = input("请输入每日定时签到时间(HH:MM)，不设置请留空：")

        print("\n=== 步骤 4: 企业微信通知配置 (可选) ===")
        print("直接回车跳过")
        corpid = input("CorpID: ")
        secret = input("Secret: ")
        agentid = input("AgentID: ")

        # Construct new data model
        new_data = {
            "accounts": [{
                "name": acc_name,
                "class_id": class_id,
                "cookie": cookie,
                "pwd": ""
            }],
            "locations": [{
                "name": loc_name,
                "lat": lat,
                "lng": lng,
                "acc": acc
            }],
            "tasks": [{
                "account_name": acc_name,
                "location_name": loc_name,
                "enable": True
            }],
            "scheduletime": scheduletime,
            "wecom": {
                "corpid": corpid,
                "secret": secret,
                "agentid": agentid,
                "touser": "@all"
            },
            "debug": False,
            "configLock": True
        }

        config.save_config(new_data)
        print("配置已保存。")
    else:
        print("----------欢迎回来----------")
        print("配置已读取")
        if not config.get("scheduletime"):
            print("当前模式：手动运行")
        else:
            print(f"当前模式：每日定时 ({config.get('scheduletime')})")

    print("----------信息----------")
    print(f"账号数量: {len(config.get('accounts', []))}")
    print(f"地点数量: {len(config.get('locations', []))}")
    print(f"任务数量: {len(config.get('tasks', []))}")
    wecom = config.get("wecom", {})
    if wecom.get("corpid"):
        print("通知方式: 企业微信 (已配置)")
    else:
        print("通知方式: 无")
    print("---------------------")

    setup_logger(config.get("debug"))
    manager = CheckInManager(config)

    scheduletime = config.get("scheduletime")
    if scheduletime:
        print("☆等待设定时间 " + scheduletime + " 到达☆")
        schedule.every().day.at(scheduletime).do(manager.run_job)

        while True:
            schedule.run_pending()
            time.sleep(10)
    else:
        manager.run_job()
        input("手动签到已结束，敲击回车关闭窗口☆~")

if __name__ == "__main__":
    main()
