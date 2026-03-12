# utils/weather_api.py
# -*- coding: utf-8 -*-
import requests

KEY = '20c4f5de754b4b2a9b475d12ccf88bd9'
mykey = '&key=' + KEY

url_api_geo = 'https://geoapi.qweather.com/v2/city/'


# 获取对应城市的id值
def get_city(city_kw):
    url_v2 = url_api_geo + 'lookup?location=' + city_kw + mykey
    city = requests.get(url_v2).json()['location'][0]

    city_id = city['id']
    district_name = city['name']
    city_name = city['adm2']
    province_name = city['adm1']
    country_name = city['country']
    lat = city['lat']
    lon = city['lon']

    return city_id, district_name, city_name, province_name, country_name, lat, lon


def weather_seven(location):
    msg = get_city(location)
    id = msg[0]
    city_name = msg[1]
    province_name = msg[3]

    print(id, city_name, province_name)
    list1 = []

    url1 = f'https://devapi.qweather.com/v7/weather/now?location={id}&key={KEY}'
    url2 = f'https://devapi.qweather.com/v7/weather/7d?location={id}&key={KEY}'
    url3 = f'https://devapi.qweather.com/v7/air/now?location={id}&key={KEY}'
    url4 = f'https://devapi.qweather.com/v7/weather/24h?location={id}&key={KEY}'
    url5 = f'https://devapi.qweather.com/v7/indices/1d?type=1,2&location={id}&key={KEY}'

    day = requests.get(url1)
    days = day.json()['now']

    air = requests.get(url3)
    airs = air.json()['now']
    air_aqi = airs['aqi']
    air_category = airs['category']

    hour_twenty = requests.get(url4).json()['hourly'][0]
    hour_later = f'一个小时后天气：{hour_twenty["text"]} {hour_twenty["temp"]}°C'

    jianjie = requests.get(url5)
    msg = jianjie.json()["daily"][0]["text"]

    weather_text = days['text']
    temp_ti = days['feelsLike']
    humidity = days['humidity']

    dic_day = {}
    dic_day['id'] = id
    dic_day['city_name'] = city_name
    dic_day['province_name'] = province_name
    dic_day['weather_text'] = weather_text
    dic_day['temp_ti'] = temp_ti + "°C"
    dic_day['humidity'] = humidity
    dic_day['air_aqi'] = f'{air_aqi} ({air_category})'
    dic_day['hour_later'] = hour_later
    dic_day['msg'] = msg

    data = requests.get(url2)
    msg = data.json()
    datas = msg['daily']
    list2 = []

    for i in datas:
        dic1 = {}
        dic1['max_temp'] = i['tempMax']
        dic1['min_temp'] = i['tempMin']
        dic1['weather_day'] = i['textDay']
        dic1['windDirDay'] = f"{i['windDirDay']}"
        dic1['windSpeedDay'] = i['windSpeedDay'] + '级'
        dic1['vis'] = i['vis']
        list2.append(dic1)

    list1.append(dic_day)
    list1.append(list2)
    return list1