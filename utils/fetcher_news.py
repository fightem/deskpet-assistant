import requests
import urllib.parse

# ================= 🚀 核心配置区 =================
COOKIES = {
    # 微博 Cookie
    "Weibo": "XSRF-TOKEN=2fXiSP-CNutl9M8tgEHQwYUA; SCF=AjrPqmIwJAo7usVdllRnVktjegt6X2BVwiquEjCcrpel11WCnQB6IAOtS93K_ZJh9RsHFNp-_67m3GUcW4xrOZo.; SUB=_2A25EqufCDeRhGeFI6VUT-SnKyDyIHXVnxmUKrDV8PUNbmtAYLXLdkW9NfSxyUx9i_usceLcwE4UoIbjRToDzPQom; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WF.ZvoXDovhpd9jOr-Vaxi05NHD95QNSozNeo.NSoe7Ws4Dqcj_i--fiK.ciKL2i--ci-z7i-zXi--fiKnRi-8Fi--fiK.piKLFi--NiKL2iKn7; ALF=02_1775641746; _s_tentry=weibo.com; Apache=2264971499819.9146.1773049854014; SINAGLOBAL=2264971499819.9146.1773049854014; ULV=1773049854016:1:1:1:2264971499819.9146.1773049854014:; WBPSESS=3v_hoLy8qpyhA1wxktmwQEl0Lvo9eMXoZh0_YmaMhhA5M2cSth9bRa-jCmkKkohKDkKcdB7y8mQtIqZj9jZdnVf3K1srQPGtK0mdghQDnGFUxw8df60W7N8C6sqNaWxCJpAjMrY3bJkp_OEtCKVumA==",

    # 知乎 Cookie
    "Zhihu": "q_c1=a3d2370ee66d424dbc5804d3401b6a43|1763020621000|1763020621000; _xsrf=w4D7aplkqsJ4jg41m9rg6a7554HZJVAr; _zap=259b7f7f-f4c9-4554-86d3-970a2b37ccf6; d_c0=Y3eUFsVJ6RuPTtTsAZ8VbvJQpS01Ac2Z8OE=|1772292171; Hm_lvt_98beee57fd2ef70ccdd5ca52b9740c49=1772421549,1772746034; HMACCOUNT=3F298C903A3BBA02; __zse_ck=005_M32BOWPbKzHzmDE54qtVlW5KkHeF6ESNN3AGzudeE2CT3iE5n5XUHB6Bt=5L1crQn5ZteXY9lLMAcJP53DW9ep4E9NQ8WNqulE/x5HEIxskkjxLoRvmTF4Q3DL0ivkg0-0Qq5sJ7+v3xCKu6OvcaVFr7iYSL+N2PGzaW0bGNFWscyLCnMklH7vkZzmcp4xNm9LciOo7JqJ6n7GgKRxiv3zSbo438PmKTMewods9CAnU6jX0bGRJMmgLFwWW7Y8PQb; Hm_lpvt_98beee57fd2ef70ccdd5ca52b9740c49=1773036213; SESSIONID=7RIl6sZg73IWSwk8fPOIHkPHKpVGeQhsGiIWJMbcSF5; JOID=VlATAUs6WQfYPq3ZESWzlt-XccoJAQVKtgzSjXIJZkCLb96-Jz7Ir7c2r9MXXByYPH-uU9PFHfKngYSMKXoDZM8=; osd=WlETAko2WAfbP6HYESaymt6XcssFAAVJtwDTjXEIakGLbN-yJj7Lrrs3r9AWUB2YP36iUtPGHP6mgYeNJXsDZ84=; z_c0=2|1:0|10:1773050992|4:z_c0|92:Mi4xOFJwVUlRQUFBQUJqZDVRV3hVbnBHeVlBQUFCZ0FsVk5URmFRYWdDSzRkLWVDNDB6RmdQRVdyMjNfblEwWFBWczlR|8525f85a7e54d88244fc6e9ae90183f4b7cb8c9783e0e959a36b02230fa0b331; BEC=4da77e64be3cf762e3831e43ab259290"
}

BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def parse_cookies(cookie_str):
    cookies = {}
    try:
        items = cookie_str.split(';')
        for item in items:
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies
    except Exception as e:
        print(f"Cookies解析失败: {e}")
        return {}

def fetch_bilibili():
    url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    res = requests.get(url, headers=BASE_HEADERS, timeout=5)
    res_json = res.json()
    results = []
    if res_json.get('code') == 0:
        for i, item in enumerate(res_json['data']['list'][:20]):
            results.append({
                "rank": str(i + 1),
                "title": item.get('title', ''),
                "author": item.get('owner', {}).get('name', '未知'),
                "hotness": f"{item.get('stat', {}).get('view', 0)} 播放",
                "link": f"https://www.bilibili.com/video/{item.get('bvid')}"
            })
    return results

def fetch_weibo():
    url = "https://weibo.com/ajax/side/hotSearch"
    weibo_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "referer": "https://weibo.com/hot/search",
        "user-agent": BASE_HEADERS['User-Agent'],
        "x-requested-with": "XMLHttpRequest"
    }

    cookie_str = COOKIES.get("Weibo", "")
    if not cookie_str:
        raise Exception("请在 config 中填入微博 Cookie。")

    cookies_dict = parse_cookies(cookie_str)

    try:
        response = requests.get(url, headers=weibo_headers, cookies=cookies_dict, timeout=10)
        response.raise_for_status()

        if "newlogin" in response.url or not response.text.startswith('{'):
            raise Exception("请求被拦截！Cookie可能已过期，请重新获取。")

        data = response.json()
    except Exception as e:
        raise Exception(f"请求失败: {str(e)}")

    result_list = []
    seen_words = set()

    hotgovs_data = data.get('data', {}).get('hotgovs', [])
    hotgov_data = data.get('data', {}).get('hotgov', {})

    for item in hotgovs_data:
        word = item.get('word', '')
        if word and word not in seen_words:
            seen_words.add(word)
            result_list.append({
                'title': word,
                'hotness': str(item.get('num', '置顶')),
                'author': '📌 置顶热搜',
                'link': f"https://s.weibo.com/weibo?q=%23{urllib.parse.quote(word)}%23"
            })

    if hotgov_data:
        word = hotgov_data.get('word', '')
        if word and word not in seen_words:
            seen_words.add(word)
            result_list.append({
                'title': word,
                'hotness': str(hotgov_data.get('num', '置顶')),
                'author': '📌 置顶热搜',
                'link': f"https://s.weibo.com/weibo?q=%23{urllib.parse.quote(word)}%23"
            })

    realtime_data = data.get('data', {}).get('realtime', [])
    for item in realtime_data:
        if 'is_ad' in item:
            continue

        word = item.get('word', '')
        if word and word not in seen_words:
            seen_words.add(word)
            hotness_val = item.get('num', item.get('raw_hot', '未知'))
            result_list.append({
                'title': word,
                'hotness': f"{hotness_val} 热度",
                'author': '🔥 实时热搜',
                'link': f"https://s.weibo.com/weibo?q=%23{urllib.parse.quote(word)}%23"
            })

        if len(result_list) >= 30:
            break

    final_results = []
    for i, item in enumerate(result_list[:30]):
        item['rank'] = str(i + 1)
        final_results.append(item)

    return final_results

def fetch_zhihu():
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=30&desktop=true"
    headers = BASE_HEADERS.copy()

    cookie_str = COOKIES.get("Zhihu", "")
    if not cookie_str:
        raise Exception("请在 config 中填入知乎 Cookie。")

    headers["Cookie"] = cookie_str

    res = requests.get(url, headers=headers, timeout=5)
    if res.status_code != 200:
        raise Exception(f"被拦截啦！状态码: {res.status_code}。可能是 Cookie 已过期。")

    try:
        res_json = res.json()
    except:
        raise Exception("知乎返回的数据格式异常。")

    results = []
    data_list = res_json.get('data', [])

    for i, item in enumerate(data_list[:30]):
        target = item.get('target', {})
        title = target.get('title', '无标题')
        hotness = item.get('detail_text', '未知热度')

        api_url = target.get('url', '')
        web_url = api_url.replace("https://api.zhihu.com/questions", "https://www.zhihu.com/question")

        results.append({
            "rank": str(i + 1),
            "title": title,
            "author": "知乎问答",
            "hotness": hotness,
            "link": web_url
        })
    return results