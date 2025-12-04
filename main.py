import random
import requests
import re
import time
import os
from bs4 import BeautifulSoup
import json
import schedule
from datetime import datetime, timedelta
import logging

# 获取当前目录
current_directory = os.getcwd()
file_name = "config.json"
file_path = os.path.join(current_directory, file_name)

print("----------提醒----------")
print("项目地址：https://github.com/JasonYANG170/AutoCheckBJMF")
print("请查看教程以获取Cookie和班级ID")
print("config.json文件位置：", current_directory)

# 检查文件是否存在
if not os.path.exists(file_path):
    # 定义默认的 JSON 数据
    default_config = {
        "class": "", # 班级ID
        "lat": "", # 纬度
        "lng": "", # 经度
        "acc": "", # 海拔
        "time": 0, # 等待时间（已弃用）
        "cookie": "", # 用户令牌
        "scheduletime": "", # 定时任务
        "pushplus": "", # pushpush推送令牌
        "debug": False, # 调试模式
        "configLock": False #配置编辑状态，
    }
    # 文件不存在，创建并写入默认数据
    with open(file_path, "w") as file:
        json.dump(default_config, file, indent=4)
    print("----------初始化----------")
    print(f"文件 {file_name} 不存在，已创建并填充默认数据。")

# 读取外部 JSON 文件中的数据
with open(file_path, 'r') as file:
    json_data = json.load(file)
    debug = json_data.get("debug", False)

    # 判断是否首次使用或解除配置锁定
    if not json_data.get('configLock'):
        print("----------基础配置(必填)----------")
        print("☆请通过查看教程抓包获取班级ID")
        ClassID = input("请输入班级ID：")
        print("☆输入的经纬度格式为x.x，请输入至少8位小数用于定位微偏移，不满8位用0替补！")
        print("☆腾讯坐标拾取工具：https://lbs.qq.com/getPoint/")
        X = input("请输入纬度(X)：")
        Y = input("请输入经度(Y)：")
        ACC = input("请输入海拔：")
        print("----------配置Cookie(必填)----------")
        print("请通过查看教程抓包获取Cookie")
        print("教程：https://github.com/JasonYANG170/AutoCheckBJMF/wiki/")
        print("登录获取：https://k8n.cn/student/login")
        print("Tip:90%的失败由Cookie变更导致")
        Cookies = []
        print("请输入你的Cookie，输入空行结束，支持用户备注格式如下")
        print("username=<备注>;remember....<魔方Cookie>")
        while True:
            cookie = input("Cookie: ")
            if not cookie:
                break
            Cookies.append(cookie)
        print("----------配置定时任务(可选)----------")
        print("格式为00:00,例如1:30要填写为01:30!不设置定时请留空")
        print("Tip：请注意以上格式并使用英文符号“:”不要使用中文符号“：”")
        scheduletime = input("请输入签到时间：")
        if scheduletime=="":
            print("您未填写签到时间，未启用定时签到，启动即开始签到")
        print("----------远程推送----------")
        pushtoken = input("(未适配新版多人签到，如果是多人签到建议不使用)\n请输入pushplus推送密钥，不需要请留空：")

        print("配置完成，您的信息将写入json文件，下次使用将直接从json文件导入")
        # 2. 修改数据
        json_data["class"] = ClassID
        json_data["lat"] = X
        json_data["lng"] = Y
        json_data["acc"] = ACC
        json_data["cookie"] = Cookies
        json_data["scheduletime"] = scheduletime
        json_data["pushplus"] = pushtoken
        json_data["configLock"] = True
        # 3. 写回JSON文件
        with open(file_path, "w") as file:
            json.dump(json_data, file, indent=4) # indent 设置缩进为4个空格
        print("数据已保存到"+current_directory+"下的data.json中。")
    else:
        print("----------欢迎回来----------")
        ClassID = json_data["class"]
        X = json_data["lat"]
        Y = json_data["lng"]
        ACC = json_data["acc"]
        Cookies = json_data["cookie"]
        scheduletime = json_data["scheduletime"]
        pushtoken = json_data["pushplus"]
        print("配置已读取")
        if scheduletime=="":
            print("当前签到模式为：手动，即将开始签到")
        else:
            print("当前签到模式为：自动，启动定时任务")
    print("----------信息----------")
    print("班级ID:" + ClassID)
    print("纬度:" + X)
    print("经度:" + Y)
    print("海拔:" + ACC)
    # print("检索间隔:" + str(SearchTime))
    print("Cookie数量:" + str(len(Cookies)))
    print("定时:" + scheduletime)
    print("通知token:" + pushtoken)
    if debug:print("Debug:" + str(debug))
    print("---------------------")

def printLog(type, message):
    if debug:
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

if debug:
    # 创建 logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # 创建文件处理器并设置编码为 UTF-8
    file_handler = logging.FileHandler('AutoCheckBJMF.log', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    # 将处理器添加到 logger
    logger.addHandler(file_handler)
    printLog("info", "已启动Debug")
print("★一切就绪，程序开始执行\\^o^/")

# 随机经纬，用于多人签到定位偏移
def modify_decimal_part(num):
    # Generates a random offset between -0.00015 and 0.00015
    # Roughly corresponds to 15 meters
    offset = random.uniform(-0.00015, 0.00015)
    return float(num) + offset

def thisTime(hour, minute):
    target_hour = int(hour)
    target_minute = int(minute)

    now = datetime.now()
    target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

    if target_time < now:
        target_time += timedelta(days=1)

    remaining = target_time - now
    remaining_seconds_main = int(remaining.total_seconds())

    remaining_hours = remaining_seconds_main // 3600
    remaining_minutes = (remaining_seconds_main % 3600) // 60
    remaining_seconds = remaining_seconds_main % 60

    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # 区分剩余时间的显示逻辑，以优化终端内容的显示阅读体验
    if remaining_seconds_main < 300:
        # 如果剩余时间小于5分钟则每秒刷新
        print("\r当前时间：{}，距离下次任务执行{:02d}:{:02d} 还剩{}分钟{}秒\t\t".format(
            current_time_str, target_hour, target_minute, remaining_minutes, remaining_seconds), end="")
        time.sleep(1)
    else:
        # 如果剩余时间大于5分钟则每分钟刷新
        print("\r当前时间：{}，距离下次任务执行{:02d}:{:02d} 还剩{}小时{}分钟\t\t".format(
            current_time_str, target_hour, target_minute, remaining_hours, remaining_minutes), end="")
        time.sleep(60)

def qiandao(theCookies):
    # title = '班级魔法自动签到任务'  # 改成你要的标题内容
    url = 'http://k8n.cn/student/course/' + ClassID + '/punchs'
    errorCookie = []
    nullCookie = 0
    # 多用户检测签到
    for uid in range(0,len(theCookies)):
        onlyCookie = theCookies[uid]

        # 使用正则表达式提取目标字符串 - 用户备注
        pattern = r'username=[^;]+'
        result = re.search(pattern, onlyCookie)

        if result:
            username_string = " <%s>"%result.group(0).split("=")[1]
        else:
            username_string = ""

        # 用户信息显示与5秒冷却
        print("☆☆☆☆☆ 用户UID：%d%s 即将签到 ☆☆☆☆☆"%(uid+1,username_string),end="")
        time.sleep(1) #暂停5秒后进行签到
        print("\r★☆☆☆☆ 用户UID：%d%s 即将签到 ☆☆☆☆★"%(uid+1,username_string),end="")
        time.sleep(1)
        print("\r★★☆☆☆ 用户UID：%d%s 即将签到 ☆☆☆★★"%(uid+1,username_string),end="")
        time.sleep(1)
        print("\r★★★☆☆ 用户UID：%d%s 即将签到 ☆☆★★★"%(uid+1,username_string),end="")
        time.sleep(1)
        print("\r★★★★☆ 用户UID：%d%s 即将签到 ☆★★★★"%(uid+1,username_string),end="")
        time.sleep(1)
        print("\r★★★★★ 用户UID：%d%s 开始签到 ★★★★★"%(uid+1,username_string))

        # 使用正则表达式提取目标字符串 - Cookie
        # Improved regex to be more generic for different hashes
        pattern = r'remember_student_[0-9a-fA-F]+=[^;]+'
        result = re.search(pattern, onlyCookie)

        if result:
            extracted_string = result.group(0)
            if debug:
                print(extracted_string)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 9; AKT-AK47 Build/USER-AK47; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 XWEB/1160065 MMWEBSDK/20231202 MMWEBID/1136 MicroMessenger/8.0.47.2560(0x28002F35) WeChat/arm64 Weixin NetType/4G Language/zh_CN ABI/arm64',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/wxpic,image/tpg,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'X-Requested-With': 'com.tencent.mm',
                'Referer': 'http://k8n.cn/student/course/' + ClassID,
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN,zh-SG;q=0.9,zh;q=0.8,en-SG;q=0.7,en-US;q=0.6,en;q=0.5',
                'Cookie': extracted_string
            }

            try:
                response = requests.get(url, headers=headers, timeout=10)
                print("响应:", response)

                # 创建 Beautiful Soup 对象解析 HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                title_tag = soup.find('title')

                if debug:
                    print("★☆★")
                    print(soup)
                    print("===")
                    print(title_tag)
                    print("★☆★")

                if title_tag and "出错" not in title_tag.text:
                    # 使用正则表达式从 HTML 文本中提取所有 punch_gps() 中的数字
                    pattern = re.compile(r'punch_gps\((\d+)\)')
                    matches = pattern.findall(response.text)
                    print("找到GPS定位签到:", matches)
                    pattern2 = re.compile(r'punchcard_(\d+)')
                    matches2 = pattern2.findall(response.text)
                    print("找到扫码签到:", matches2)
                    matches.extend(matches2)
                    if matches:
                        for match in matches:
                            url1 = "http://k8n.cn/student/punchs/course/" + ClassID + "/" + match
                            newX = modify_decimal_part(X)
                            newY = modify_decimal_part(Y)
                            payload = {
                                'id': match,
                                'lat': newX,
                                'lng': newY,
                                'acc': ACC,  #未知，可能是高度
                                'res': '',  #拍照签到
                                'gps_addr': ''  #未知，抓取时该函数为空
                            }

                            try:
                                response = requests.post(url1, headers=headers, data=payload, timeout=10)
                                print("签到请求已发送： 签到ID[%s] 签到定位[%s,%s] 签到海拔[%s]"%(match, newX, newY, ACC))
                                printLog("info", "用户UID[%d%s] | 签到请求已发送： 签到ID[%s] 签到定位[%s,%s] 签到海拔[%s]"%(uid+1, username_string, match, newX, newY, ACC))

                                if response.status_code == 200:
                                    print("请求成功，响应:", response)

                                    # 解析响应的 HTML 内容
                                    soup_response = BeautifulSoup(response.text, 'html.parser')
                                    # h1_tag = soup_response.find('h1')
                                    div_tag = soup_response.find('div', id='title')

                                    if debug:
                                        print("★☆★")
                                        print(soup_response)
                                        print("===")
                                        print(div_tag)
                                        print("★☆★")

                                    if div_tag:
                                        h1_text = div_tag.text
                                        print(h1_text)
                                        printLog("info", "用户UID[%d%s] | %s"%(uid+1, username_string, h1_text))
                                        # encoding:utf-8
                                        if pushtoken != "" and h1_text== "签到成功":
                                            url = 'http://www.pushplus.plus/send?token=' + pushtoken + '&title=' + "班级魔法自动签到任务" + '&content=' + h1_text  # 不使用请注释
                                            try:
                                                requests.get(url, timeout=10)  # 不使用请注释
                                            except Exception as e:
                                                print(f"推送失败: {e}")
                                                printLog("error", f"推送失败: {e}")
                                        continue  # 返回到查找进行中的签到循环
                                    else:
                                        print("未找到 <h1> 标签，可能存在错误")
                                        printLog("info", "用户UID[%d%s] | 未找到 <h1> 标签，可能存在错误或签到成功"%(uid+1, username_string))
                                else:
                                    print("请求失败，状态码:", response.status_code)
                                    printLog("error", "用户UID[%d%s] | 请求失败，状态码: %d"%(uid+1, username_string, response.status_code))
                                    print("将本Cookie加入重试队列")
                                    errorCookie.append(onlyCookie)
                            except requests.RequestException as e:
                                print(f"POST请求异常: {e}")
                                printLog("error", f"用户UID[{uid+1}{username_string}] | POST请求异常: {e}")
                                errorCookie.append(onlyCookie)
                    else:
                        print("未找到在进行的签到")
                else:
                    print("登录状态异常，将本Cookie加入重试队列")
                    printLog("error", "用户UID[%d%s] | 登录状态异常"%(uid+1, username_string))
                    errorCookie.append(onlyCookie)
            except requests.RequestException as e:
                print(f"GET请求异常: {e}")
                printLog("error", f"用户UID[{uid+1}{username_string}] | GET请求异常: {e}")
                errorCookie.append(onlyCookie)
        else:
            nullCookie += 1
            print("未找到匹配的字符串，检查Cookie是否错误！")
    return errorCookie, nullCookie

def job():
    current_time = datetime.now()
    print("\n进入检索，当前时间为:", current_time)

    errorCookie,nullCookie = qiandao(Cookies)
    if len(errorCookie)>0:
        print("检测到有Cookie签到失败，等待5分钟后启动一次重试队列")
        time.sleep(300)
        errorCookie = qiandao(errorCookie)
        if len(errorCookie)>0:
            print("检测到仍然有Cookie签到失败，等待15分钟后最后启动一次重试队列")
            time.sleep(900)
            errorCookie = qiandao(errorCookie)
            if len(errorCookie)>0:
                print("!!!  检测到仍然有Cookie签到失败，请检查Cookie是否过期或网络异常  !!!")
    elif nullCookie>0:
        print("!!! 本次签到存在异常，请检查Cookie是否均已正常配置 !!!")
    else:
        print("★本次签到圆满成功★")

    print("■ □ ■ □ ■ □ 我是分割线 □ ■ □ ■ □ ■")

    if scheduletime:
        print("☆本次签到结束，等待设定的时间%s到达☆\n"%scheduletime)

if (scheduletime != ""):
    print("☆等待设定时间" + scheduletime + "到达☆")
    # 设置定时任务，在每天的早上8点触发
    schedule.every().day.at(scheduletime).do(job)
    # 格式化时间
    hour,minute = scheduletime.split(":")

    while True:
        schedule.run_pending()
        thisTime(hour,minute) # 倒计时
else:
    job()
    input("手动签到已结束，敲击回车关闭窗口☆~")
