from core import ConfigManager, CheckInManager, setup_logger
import schedule
import time
import os

def main():
    print("----------提醒----------")
    print("项目地址：https://github.com/JasonYANG170/AutoCheckBJMF")
    print("请查看教程以获取Cookie和班级ID")
    print("config.json文件位置：", os.getcwd())

    config = ConfigManager()

    # CLI setup if not locked
    if not config.get("configLock"):
        print("----------基础配置(必填)----------")
        print("☆请通过查看教程抓包获取班级ID")
        class_id = input("请输入班级ID：")
        print("☆输入的经纬度格式为x.x，请输入至少8位小数用于定位微偏移，不满8位用0替补！")
        print("☆腾讯坐标拾取工具：https://lbs.qq.com/getPoint/")
        x = input("请输入纬度(X)：")
        y = input("请输入经度(Y)：")
        acc = input("请输入海拔：")

        print("----------配置Cookie(必填)----------")
        cookies = []
        print("请输入你的Cookie，输入空行结束，支持用户备注格式如下")
        print("username=<备注>;remember....<魔方Cookie>")
        while True:
            c = input("Cookie: ")
            if not c:
                break
            cookies.append(c)

        print("----------配置定时任务(可选)----------")
        print("格式为00:00,例如1:30要填写为01:30!不设置定时请留空")
        scheduletime = input("请输入签到时间：")

        print("----------远程推送----------")
        pushtoken = input("(未适配新版多人签到，如果是多人签到建议不使用)\n请输入pushplus推送密钥，不需要请留空：")

        data = {
            "class": class_id,
            "lat": x,
            "lng": y,
            "acc": acc,
            "cookie": cookies,
            "scheduletime": scheduletime,
            "pushplus": pushtoken,
            "debug": False,
            "configLock": True
        }
        config.save_config(data)
        print("数据已保存到 config.json 中。")
    else:
        print("----------欢迎回来----------")
        print("配置已读取")
        if not config.get("scheduletime"):
            print("当前签到模式为：手动，即将开始签到")
        else:
            print("当前签到模式为：自动，启动定时任务")

    print("----------信息----------")
    print("班级ID:" + config.get("class"))
    print("纬度:" + config.get("lat"))
    print("经度:" + config.get("lng"))
    print("海拔:" + config.get("acc"))
    print("Cookie数量:" + str(len(config.get("cookie", []))))
    print("定时:" + config.get("scheduletime"))
    print("通知token:" + config.get("pushplus"))
    print("---------------------")

    setup_logger(config.get("debug"))
    manager = CheckInManager(config)

    scheduletime = config.get("scheduletime")
    if scheduletime:
        print("☆等待设定时间" + scheduletime + "到达☆")
        schedule.every().day.at(scheduletime).do(manager.run_job)

        while True:
            schedule.run_pending()
            # Minimal countdown logic for CLI
            time.sleep(1)
    else:
        manager.run_job()
        input("手动签到已结束，敲击回车关闭窗口☆~")

if __name__ == "__main__":
    main()
