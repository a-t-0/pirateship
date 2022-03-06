#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2022 i7heaven <caifangmao8@gmail.com>
#
# Distributed under terms of the MIT license.

import requests, re, json, sys, subprocess, urllib
from tabulate import tabulate
from os.path import expanduser

PIRATE_URL = "https://thepiratebay.org"
PIRATE_API_URL = "https://apibay.org"

MAGNET_FORMAT = "magnet:?xt=urn:btih:{}&dn={}"

PROXY_HOST=''
PROXY_PORT=''

MAIN_CAT = {'0' : '???'}
SUB_CAT = {'0' : '???'}

raw_main_js = None

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


def get_readable_size(size, decimal_places=2):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0 or unit == 'PiB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def ensure_main_js():
    global raw_main_js
    if raw_main_js == None:
        raw_main_js = request(PIRATE_URL + "/static/main.js")

def fillin_categories():
    global raw_main_js
    ensure_main_js()

    raw_categories = ""
    for main_line in raw_main_js.iter_lines():
        if re.search("function print_category", str(main_line)):
            raw_categories = main_line.decode("utf-8")

    if len(raw_categories) > 0:
        pattern = "cc\[0\]==[0-9]{1}\)main='[a-zA-Z0-9-_ \(\)\/]+'|cat==[0-9]{3}\)return maintxt\+'[a-zA-Z0-9-_ \(\)\/]*'"
        matches = re.findall(pattern, raw_categories)
        for match in matches:
            if match.startswith("cc[0]"):
                num = "(?!cc\[0\]==)[0-9]{1}(?=\))"
                ptn = "(?!main=')[a-zA-Z0-9-_ \(\)\/]+(?=')"
                cc_matches = re.findall(ptn, match)
                num_matches = re.findall(num, match)
                MAIN_CAT[num_matches[0]] = cc_matches[0]
            else:
                num = "(?!cat==)[0-9]{3}(?=\))"
                ptn = "(?!maintxt\+')[a-zA-Z0-9-_ \(\)\/]+(?=')"
                cat_matches = re.findall(ptn, match)
                num_matches = re.findall(num, match)
                SUB_CAT[num_matches[0]] = cat_matches[0]

def get_trackers():
    global raw_main_js
    ensure_main_js()
    tracker_list = []

    raw_trackers = ""
    for main_line in raw_main_js.iter_lines():
        if re.search("function print_trackers", str(main_line)):
            raw_trackers = main_line.decode("utf-8")

    if len(raw_trackers) > 0:
        pattern = "(?!encodeURIComponent\()[^\(]+(?=\))"
        matches = re.findall(pattern, raw_trackers)
        if len(matches) > 0:
            for tracker in matches:
                tracker_list.append(urllib.parse.unquote(tracker.replace("'", "")))

    return tracker_list

def get_category(category_num):
    main = MAIN_CAT[category_num[:1]]
    sub = SUB_CAT[category_num]
    
    return main + " > " + sub


def get_search_result_list(keyword):
    result_list = []
    converted_keyword = keyword.replace(' ', '+')
    search = {'q' : converted_keyword, 'cat' : '0'}
    raw_search_results = request(PIRATE_API_URL + "/q.php", search)
    return json.loads(raw_search_results.content)

def search(keyword):
    fillin_categories()
    tracker_list = get_trackers()
    search_result = get_search_result_list(keyword)

    results = []
    link_results = []
    i = 0
    for search in search_result:
        magnet_link = MAGNET_FORMAT.format(search["info_hash"], urllib.parse.quote(search["name"]))
        for tracker in tracker_list:
            magnet_link = magnet_link + "&tr=" + urllib.parse.quote_plus(tracker)

        results.append([i, get_category(search["category"]), search["name"], get_readable_size(int(search["size"]))])
        link_results.append(magnet_link)
        i = i + 1

    if len(results) > 0:
        final_output = tabulate(results, headers=['编号', '类型', '名称', '大小'], tablefmt="grid")
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
                        add_to_syno = input("是否添加到群辉(y/n)")
                        if add_to_syno == "y":
                            add_task = subprocess.Popen([expanduser("~") + "/bin/synology.sh", "add", link_results[selected_index]],
                                                        stdout=subprocess.PIPE,
                                                        stderr=subprocess.PIPE)

                            stdout, stderr = add_task.communicate()
                            print(stdout)
                            print(stderr)
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
