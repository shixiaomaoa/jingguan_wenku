import time
import random
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from enum import Enum
import csv
import json


# 创建枚举类
class WriteToType(Enum):
    CSV = 1
    JSON = 2


# 创建CSV文件
def write_csv(elements):
    with open("jg_wenku.csv", "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["分类", "标题", "附件链接", "发帖人", "发表时间", "浏览量", "评论量"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(elements)
    print("文库信息已写入jg_wenku.csv")


# 创建JSON文件
def write_json(elements):
    with open("jg_wenku.json", "w", newline="", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print("文库信息已写入jg_wenku.json")


# 分页逻辑，爬取82页,最多刷新不超过3次
def page_parse():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            wait = WebDriverWait(driver, timeout=10, poll_frequency=0.5)
            next_btn = wait.until(
                EC.visibility_of_element_located((By.XPATH, ".//div[@class='pg']/a[@class='nxt']"))
            )
            next_btn.click()
            # 关键：等待新页面的 .xst 元素出现
            time.sleep(random.uniform(5, 7))
            return True
        except Exception as e:
            print(f"翻页异常 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                try:
                    # 刷新页面后重新定位下一页按钮
                    driver.refresh()
                    time.sleep(3)
                except:
                    pass
            else:
                return False
    return False


# 构建字典
def create_dict(category, title, watch_counting, review_counting, extra_url, author, publish_time):
    info_dict = {
        "分类": category,
        "标题": title,
        "附件链接": extra_url,
        "发帖人": author,
        "发表时间": publish_time,
        "浏览量": watch_counting,
        "评论量": review_counting
    }
    return info_dict


# 处理发布日期
def handle_publish_time(publish_time):
    now = datetime.now()
    if "分钟" in publish_time:
        minutes = int(publish_time.replace("分钟前", "").strip())
        dt = now - timedelta(minutes=minutes)
        return dt.strftime("%Y-%m-%d")
    elif "小时" in publish_time:
        hours = int(publish_time.replace("小时前", "").replace(" ", ""))
        dt = now - timedelta(hours=hours)
        return dt.strftime("%Y-%m-%d")
    elif "昨天" in publish_time:
        yesterday = now - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")
    elif "刚刚" in publish_time:
        return now.strftime("%Y-%m-%d")
    elif "-" in publish_time:
        return publish_time
    else:
        return "无发布日期"


# 爬取文库信息
def scrape_info():
    count_this_page = 0
    try:
        wait = WebDriverWait(driver, timeout=15, poll_frequency=0.5)
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "xst")))

        data = driver.find_element(By.CSS_SELECTOR, "table[summary*='forum']")
        info_list = data.find_elements(By.XPATH, ".//tbody/tr/td[2]")

        for info_ in info_list:
            # 关键修复：跳过空元素
            try:
                # 先检查是否有 .xst 子元素，没有就跳过
                title_element = info_.find_element(By.CLASS_NAME, "xst")
                title = title_element.text.strip()
            except:
                continue  # 没有标题的空元素，直接跳过

            try:
                category = info_.find_element(By.XPATH, ".//em[1]/a").text.strip()
            except:
                category = "无分类"

            try:
                watch_counting = info_.find_element(By.CSS_SELECTOR, ".y.ck").text.strip()
            except:
                watch_counting = "0"

            try:
                review_counting = info_.find_element(By.CSS_SELECTOR, ".y.hf").text.strip()
            except:
                review_counting = "0"

            try:
                extra_url_element = info_.find_element(By.XPATH, ".//img[1]")
                extra_url = extra_url_element.get_attribute("src")
            except:
                extra_url = "无链接"

            try:
                author = info_.find_element(By.XPATH, "./p[1]/em[3]/a[1]").text.strip()
            except:
                author = "未知"

            try:
                publish_time_element = info_.find_element(By.XPATH, "./p[1]/em[3]/span").get_attribute("title")
                publish_time = handle_publish_time(publish_time_element)
            except:
                publish_time = "无发布日期"

            info_dict = create_dict(category, title, watch_counting, review_counting, extra_url, author, publish_time)
            final_dict.append(info_dict)
            count_this_page += 1
            time.sleep(0.3)

    except Exception as e:
        print(f"页面解析异常: {e}")
    return count_this_page


# 关键节点截取
def print_milestone(total):
    """当总采集数达到里程碑时打印醒目提示"""
    milestones = [2000, 4000, 6000, 8000]
    if total in milestones:
        print("\n" + "=" * 40)
        print(f"完成! 共采集 {total} 条")
        print("=" * 40 + "\n")


if __name__ == '__main__':
    service = Service("D:/WebDriver/msedgedriver.exe")
    driver = webdriver.Edge(service=service)
    driver.get("https://bbs.pinggu.org/forum-2177-1.html")
    driver.maximize_window()
    time.sleep(5)

    final_dict = []  # 存储所有采集到的数据
    total_count = 0  # 累计采集总数
    current_page = 1  # 当前页号
    max_page = 82  # 最大页数
    target_total = 8000  # 目标采集总数，达到后停止

    while current_page <= max_page and total_count < target_total:
        print(f"正在采集第 {current_page} 页 ...")
        added = scrape_info()
        total_count += added
        print_milestone(total_count)

        if total_count >= target_total:
            print(f"已达到目标采集数量 {target_total} 条，停止爬取。")
            break
        if current_page == max_page:
            print(f"已达到最大页数 {max_page} 页，停止翻页。")
            break

        # 点击下一页，若失败则终止循环
        if not page_parse():
            print("无法继续翻页，采集结束。")
            break
        current_page += 1

    print(f"\n全部采集完成！共采集 {len(final_dict)} 条数据，共翻到第 {current_page} 页。")
    driver.quit()
    print("请选择输出格式：")
    print("1. CSV 文件")
    print("2. JSON 文件")
    choice = input("请输入数字 1 或 2：").strip()

    if choice == "1":
        write_csv(final_dict)  # 写入 jg_wenku.csv
    elif choice == "2":
        write_json(final_dict)  # 写入 jg_wenku.json
    else:
        print("输入无效，不保存文件。")
