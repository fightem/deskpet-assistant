import argparse
import requests
import json
import time
import os
from datetime import datetime, timedelta
import urllib3

# 忽略 SSL 证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 关键词配置（用于匹配第五列"匹配关键词"）
TRADE_KEYWORDS = ["出售", "转让", "求购", "收购", "买卖", "教材", "书籍", "健身卡", "会员卡", "闲置", "低价", "转让"]
ACADEMIC_KEYWORDS = ["竞赛", "组队", "学术", "论文", "建模", "考试", "复习", "课程", "作业", "考研", "考公"]


class ZanaoCrawler:
    """
    针对 `c.zanao.com` 的帖子爬虫（不生成Excel，返回格式化数据）
    """

    def __init__(self, test_time_bound=None):
        self.test_time_bound = test_time_bound
        self.args = None
        self.posts = []  # 存储原始爬取数据
        self.formatted_posts = []  # 存储格式化后的数据（表格专用）
        self.json_filename = None

        self._parse_args_or_test()
        self._config_requests()
        self._calculate_time_parameters()

    def _parse_args_or_test(self):
        """统一处理命令行模式和测试模式的参数"""
        if self.test_time_bound is not None:
            self.time_bound_input = self.test_time_bound
        else:
            parser = argparse.ArgumentParser(
                description="从 'c.zanao.com' 爬取帖子，直到指定的时间界限（精确到时分秒）。"
            )
            parser.add_argument(
                'time_bound',
                type=str,
                help="爬取的时间界限，格式为 'YYYY-MM-DD HH:mm:ss'（例如：2025-11-20 14:30:00）"
            )
            self.args = parser.parse_args()
            self.time_bound_input = self.args.time_bound

    def _config_requests(self):
        """配置请求头和 Cookie（请根据实际情况更新 user_token）"""
        self.headers = {
            'Host': 'c.zanao.com',
            'x-sc-version': '3.1.0',
            'accept': 'application/json, text/plain, */*',
            'x-requested-with': 'XMLHttpRequest',
            'x-sc-platform': 'android',
            'x-sc-alias': 'whut',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'referer': 'https://c.zanao.com/p/home?cid=whut',
            'accept-language': 'zh-CN,zh;q=0.9',
        }
        self.cookies = {
            'user_token': 'bFdWc1pwZVpZbXlibG9Tb3BucG5pY2VqejNpTWFIS3ViSmM9',
            'Hm_lvt_44d055a19f3943caa808501f424e662e': '1763708815',
            'Hm_lpvt_44d055a19f3943caa808501f424e662e': '1763708815',
            'HMACCOUNT': 'D32C4935C0BFC648',
            'SERVERID': '68b9f2a4f058c9312f6ca1aac95ca3b1|1763710149|1763708816',
        }

    def _calculate_time_parameters(self):
        """计算时间参数"""
        try:
            self.time_bound_dt = datetime.strptime(self.time_bound_input, '%Y-%m-%d %H:%M:%S')
            self.time_bound_str = self.time_bound_dt.strftime('%Y%m%d%H%M%S')
            self.stop_crawl_ts = int(self.time_bound_dt.timestamp())

            self.run_start_dt = datetime.now()
            self.run_start_time_str = self.run_start_dt.strftime('%Y%m%d%H%M%S')

            mode = "测试模式" if self.test_time_bound is not None else "命令行模式"
            print("=" * 60)
            print(f"--- 爬虫初始化完成（{mode}）---")
            print(f"爬虫开始时间: {self.run_start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"爬取终止条件: 帖子发布时间早于或等于 {self.time_bound_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)

        except ValueError:
            print(f"错误：时间格式不正确！请使用 'YYYY-MM-DD HH:mm:ss' 格式，例如 '2025-11-20 14:30:00'。")
            exit(1)

    def _extract_keywords(self, title, content):
        """提取匹配关键词（根据标题和内容匹配买卖/学术关键词）"""
        all_text = title + " " + content
        matched_keywords = set()  # 用集合去重

        # 匹配买卖类关键词
        for keyword in TRADE_KEYWORDS:
            if keyword in all_text:
                matched_keywords.add(keyword)

        # 匹配学术类关键词
        for keyword in ACADEMIC_KEYWORDS:
            if keyword in all_text:
                matched_keywords.add(keyword)

        # 无匹配关键词时返回"无"
        return ",".join(matched_keywords) if matched_keywords else "无"

    def _format_posts(self):
        """格式化爬取数据（适配表格的5列格式）"""
        self.formatted_posts = []
        for post in self.posts:
            # 格式化每一列数据
            publish_time = datetime.fromtimestamp(int(post.get('p_time', 0))).strftime('%Y-%m-%d %H:%M:%S')
            title = post.get('title', '')
            content = post.get('content', '').strip().replace('\n', ' ')[:200]  # 内容截取前200字
            comment_count = str(post.get('c_count', '0'))
            keywords = self._extract_keywords(title, content)

            # 按表格顺序添加：[发布时间, 帖子标题, 帖子内容, 评论数目, 匹配关键词]
            self.formatted_posts.append([publish_time, title, content, comment_count, keywords])

    def crawl(self):
        """核心爬取逻辑"""
        print("\n[开始爬取] 正在获取帖子数据...")
        current_from_time = int(self.run_start_dt.timestamp())
        page_count = 1

        while True:
            params = {
                'from_time': current_from_time,
                'hot': '1',
                'isIOS': 'false',
            }

            try:
                response = requests.get(
                    'https://c.zanao.com/sc-api/thread/v2/list',
                    params=params,
                    headers=self.headers,
                    cookies=self.cookies,
                    verify=False,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                if data.get('errno') != 0:
                    print(f"[爬取失败] API 请求错误: {data.get('errmsg', '未知错误')}")
                    break

                current_page_posts = data.get('data', {}).get('list', [])

                if not current_page_posts:
                    print(f"[爬取结束] 第 {page_count} 页无数据，已获取全部符合条件的帖子")
                    break

                print(f"[第 {page_count} 页] 获取到 {len(current_page_posts)} 条帖子")

                earliest_post_ts = int(current_page_posts[-1].get('p_time', 0))
                earliest_post_time = datetime.fromtimestamp(earliest_post_ts).strftime('%Y-%m-%d %H:%M:%S')

                if earliest_post_ts <= self.stop_crawl_ts:
                    print(f"[时间界限触发] 检测到最早帖子时间 {earliest_post_time} ≤ 设定界限，开始筛选有效数据")
                    valid_posts = [
                        post for post in current_page_posts
                        if int(post.get('p_time', 0)) > self.stop_crawl_ts
                    ]
                    self.posts.extend(valid_posts)
                    print(f"[第 {page_count} 页] 筛选后有效帖子 {len(valid_posts)} 条")
                    break

                self.posts.extend(current_page_posts)
                print(f"[累计有效] 已获取 {len(self.posts)} 条帖子")

                current_from_time = earliest_post_ts
                page_count += 1
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                print(f"[网络异常] 爬取第 {page_count} 页时出错: {e}")
                break
            except Exception as e:
                print(f"[数据解析异常] 爬取第 {page_count} 页时出错: {e}")
                break

        # 爬取完成后格式化数据
        self._format_posts()
        print(f"\n[爬取总结] 共获取 {len(self.formatted_posts)} 条符合条件的帖子（已格式化）")

    def save_to_json(self):
        """保存为 JSON 文件（可选，保留该功能）"""
        if not self.posts:
            print("[JSON 保存] 无数据，跳过保存")
            return

        self.json_filename = f"{self.time_bound_str}-{self.run_start_time_str}-{len(self.posts)}.json"
        try:
            with open(self.json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.posts, f, ensure_ascii=False, indent=4)
            print(f"[JSON 保存成功] 文件路径: {os.path.abspath(self.json_filename)}")
        except Exception as e:
            print(f"[JSON 保存失败] 错误: {e}")

    def get_formatted_posts(self):
        """对外提供格式化后的数据（供PyQt表格使用）"""
        return self.formatted_posts

    def run(self):
        """执行完整流程（不生成Excel）"""
        try:
            self.crawl()
            # self.save_to_json()  # 保留JSON保存功能，可注释取消
            print("\n" + "=" * 60)
            print("爬虫任务执行完毕！")
            print("=" * 60)
        except Exception as e:
            print(f"\n[致命错误] 爬虫执行中断: {e}")


def main_test():
    """测试专用 main 函数"""
    TEST_TIME_BOUND = "2025-11-20 14:30:00"
    print("=" * 60)
    print("=== 启动爬虫测试模式 ===")
    print(f"测试时间界限: {TEST_TIME_BOUND}")
    print("=" * 60)

    crawler = ZanaoCrawler(test_time_bound=TEST_TIME_BOUND)
    crawler.run()
    # 测试获取格式化数据
    formatted_data = crawler.get_formatted_posts()
    print(f"\n格式化数据示例（前2条）:")
    for i, data in enumerate(formatted_data[:2]):
        print(f"第{i + 1}条: {data}")


if __name__ == "__main__":
    main_test()