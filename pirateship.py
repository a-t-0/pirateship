#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2022 i7heaven <caifangmao8@gmail.com>
#
# Distributed under terms of the MIT license.

import requests, re, json, sys
from tabulate import tabulate
from os.path import expanduser

PIRATE_URL = "https://thepiratebay.org"
PIRATE_API_URL = "https://apibay.org"

MAGNET_FORMAT = "magnet:?xt=urn:btih:{}&dn={}"

PROXY_HOST=''
PROXY_PORT=''

try:
    with open(expanduser("~") + "/.pirateship/config") as f:
        for line in f.readlines():
            if not line.find("PROXY_HOST=") == -1:
                PROXY_HOST = line[11:]
            elif not line.find("PROXY_PORT=") == -1:
                PROXY_PORT = line[11:]
except FileNotFoundError:
    pass

def request(url, params={}):
    if len(PROXY_HOST) > 0 and len(PROXY_PORT) > 0:
        return requests.get(url, params, proxies=dict(http="socks5h://" + PROXY_HOST + ":" + PROXY_PORT, https="socks5h://" + PROXY_HOST + ":" + PROXY_PORT))
    else:
        return requests.get(url, params)

def get_trackers():
    tracker_list = []
    raw_main = request(PIRATE_URL + "/static/main.js")
    raw_main_content = raw_main.content

    raw_trackers = ""
    for main_line in raw_main.iter_lines():
        if re.search("function print_trackers", str(main_line)):
            raw_trackers = main_line.decode("utf-8")

    if len(raw_trackers) > 0:
        pattern = "(?!encodeURIComponent\()[^\(]+(?=\))"
        matches = re.findall(pattern, raw_trackers)
        if len(matches) > 0:
            for tracker in matches:
                tracker_list.append(tracker.replace("'", ""))

    return tracker_list

def get_search_result_list(keyword):
    result_list = []
    converted_keyword = keyword.replace(' ', '+')
    search = {'q' : converted_keyword, 'cat' : '0'}
    raw_search_results = request(PIRATE_API_URL + "/q.php", search)
    return json.loads(raw_search_results.content)

def search(keyword):
    tracker_list = get_trackers()
    search_result = get_search_result_list(keyword)

    results = []
    link_results = []
    i = 0
    for search in search_result:
        magnet_link = MAGNET_FORMAT.format(search["info_hash"], search["name"])
        for tracker in tracker_list:
            magnet_link = magnet_link + "&tr=" + tracker

        results.append([i, search["name"], search["info_hash"]])
        link_results.append(magnet_link)
        i = i + 1

    if len(results) > 0:
        final_output = tabulate(results, headers=['编号', '名称', '哈希'], tablefmt="grid")
        print(final_output)

        while 1:
            option = input("选择编号或输入exit退出:")
            if option == "exit":
                exit(0)
            else:
                try:
                    selected_index = int(option)
                    if selected_index < len(link_results) and selected_index >= 0:
                        print("链接:" + link_results[selected_index])
                        break;
                    else:
                        raise ValueError("")
                except ValueError:
                    print("编号错误, 请重新输入")
                except KeyboardInterrupt:
                    exit(0);




if __name__ == "__main__":
    if len(sys.argv) > 1:
        search(sys.argv[1])
    else:
        print("缺少搜索关键字!")
