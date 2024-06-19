from matplotlib import pyplot as plt
from spyre import server

import pandas as pd
import urllib.request
import json
import os
import io
import cherrypy
import socket
from datetime import datetime, timedelta


# Функція для завантаження даних
def download_data():
    ids = {1: 22, 2: 24, 3: 23, 4: 25, 5: 3, 6: 4, 7: 8, 8: 19, 9: 20, 10: 21, 11: 9, 13: 10, 14: 11, 15: 12, 16: 13,
           17: 14, 18: 15, 19: 16, 21: 17, 22: 18, 23: 6, 24: 1, 25: 2, 26: 7, 27: 5}
    dfs = []
    headers = ['Year', 'Week', 'SMN', 'SMT', 'VCI', 'TCI', 'VHI', 'Region_ID']

    for i in ids.keys():
        id = ids[i]

        url = 'https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/get_TS_admin.php?country=UKR&provinceID={}&year1=1981&year2=2020&type=Mean'.format(i)
        wp = urllib.request.urlopen(url)
        text = wp.read()

        text = text.replace(b"<br>", b"")
        text = text.replace(b"<tt><pre>", b"")
        text = text.replace(b"</pre></tt>", b"")

        text = text.decode('utf-8')
        text = io.StringIO(text)

        df = pd.read_csv(text, header=1, names=headers)
        df = df.drop(df.loc[df['VHI'] == -1].index)
        df['Region_ID'] = id
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


# Перевірка, чи файл вже існує
if not os.path.isfile("df.csv"):
    df = download_data()
    df.to_csv('df.csv')


# Функція для конвертації тижня в дату
def week_to_date(year, week_num):
    first_day_of_year = datetime(int(year), 1, 1)
    date = first_day_of_year + timedelta(days=(week_num - 1) * 7)
    return date


# Клас для візуалізації даних
class SimpleApp(server.App):
    title = "Візуалізація даних NOAA"

    region_options = [
        {"label": "Вінницька", "value": "1"},
        {"label": "Волинська", "value": "2"},
        {"label": "Дніпропетровська", "value": "3"},
        {"label": "Донецька", "value": "4"},
        {"label": "Житомирська", "value": "5"},
        {"label": "Закарпатська", "value": "6"},
        {"label": "Запорізька", "value": "7"},
        {"label": "Івано-Франківська", "value": "8"},
        {"label": "Київська", "value": "9"},
        {"label": "Кіровоградська", "value": "10"},
        {"label": "Луганська", "value": "11"},
        {"label": "Львівська", "value": "12"},
        {"label": "Миколаївська", "value": "13"},
        {"label": "Одеська", "value": "14"},
        {"label": "Полтавська", "value": "15"},
        {"label": "Рівненська", "value": "16"},
        {"label": "Сумська", "value": "17"},
        {"label": "Тернопільська", "value": "18"},
        {"label": "Харківська", "value": "19"},
        {"label": "Херсонська", "value": "20"},
        {"label": "Хмельницька", "value": "21"},
        {"label": "Черкаська", "value": "22"},
        {"label": "Чернівецька", "value": "23"},
        {"label": "Чернігівська", "value": "24"},
        {"label": "Республіка Крим", "value": "25"}
    ]

    inputs = [
        {
            "type": 'dropdown',
            "label": 'Показник NOAA',
            "options": [{"label": "VCI", "value": "VCI"},
                        {"label": "TCI", "value": "TCI"},
                        {"label": "VHI", "value": "VHI"}],
            "key": 'ticker',
            "action_id": 'update_data'
        },
        {
            "type": 'dropdown',
            "label": 'Регіон',
            "options": region_options,
            "key": 'region',
            "action_id": 'update_data'
        },
        {
            "type": 'text',
            "label": 'Діапазон років',
            "key": 'years',
            "value": '2005-2010',
            "action_id": 'update_data'
        },
        {
            "type": 'text',
            "label": 'Діапазон тижнів',
            "key": 'weeks',
            "value": '9-35',
            "action_id": 'update_data'
        }
    ]

    controls = [{"type": "hidden", "id": "update_data"}]

    tabs = ["Графік", "Таблиця"]

    outputs = [
        {
            "type": 'plot',
            "id": 'plot',
            "control_id": 'update_data',
            "tab": 'Графік',
            "on_range_load": True
        },
        {
            "type": 'table',
            "id": 'table',
            "control_id": 'update_data',
            "tab": 'Таблиця',
            "on_page_load": True
        }
    ]

    def getData(self, params):
        df = pd.read_csv("df.csv")
        ticker = params['ticker']
        region = int(params['region'])

        years = params['years'].split('-')
        if len(years) == 2:
            start_year = int(years[0])
            end_year = int(years[1])
        elif len(years) == 1:
            if years[0]:
                start_year = end_year = int(years[0])
            else:
                start_year = end_year = 1982
        else:
            start_year = end_year = 1982

        weeks = params['weeks'].split('-')
        if start_year == end_year:
            if len(weeks) == 2:
                start_week = int(weeks[0])
                end_week = int(weeks[1])
            elif len(weeks) == 1:
                if weeks[0]:
                    start_week = end_week = int(weeks[0])
                else:
                    start_week, end_week = 1, 52
            else:
                start_week, end_week = 1, 52
        else:
            start_week, end_week = 1, 52

        if start_year > end_year:
            start_year, end_year = end_year, start_year
        if start_week >= end_week:
            start_week, end_week = end_week, start_week

        data = df[(df['Region_ID'] == region) & (df['Year'] >= start_year) & (df['Year'] <= end_year) & (df['Week'] >= start_week) & (df['Week'] <= end_week)]
        data.loc[:, 'Date'] = data.apply(lambda row: week_to_date(row['Year'], row['Week']), axis=1)
        data = data[['Date', 'Year', 'Week', ticker, 'Region_ID']]

        return data

    def getPlot(self, params):
        df = self.getData(params).set_index('Date')
        ticker = params['ticker']
        region = next((item["label"] for item in self.region_options if item["value"] == params['region']), None)

        plt_obj = df.plot(y=ticker, figsize=(24, 10), marker='o', markersize=5)
        plt_obj.set_ylabel(ticker)
        plt_obj.set_title(f'{ticker} в {region}')

        fig = plt_obj.get_figure()
        return fig


# Функція для перевірки, чи використовується порт
def check_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


# Запуск додатку
if __name__ == '__main__':
    port = 9094
    while check_port_in_use(port):
        port += 1
    cherrypy.config.update({'server.socket_port': port, 'engine.autoreload.on': False})
    app = SimpleApp()
    app.launch(port=port)
