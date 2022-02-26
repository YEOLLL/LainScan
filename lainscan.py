#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import aiofiles
import aiohttp
import click
from rich.console import Console
from rich.table import Column, Table

AUTHOR = 'Yeol'
VERSION = '0.1'
BANNER = f'''[cyan]

 ██▓    ▄▄▄       ██▓ ███▄    █   ██████  ▄████▄   ▄▄▄       ███▄    █ 
▓██▒   ▒████▄    ▓██▒ ██ ▀█   █ ▒██    ▒ ▒██▀ ▀█  ▒████▄     ██ ▀█   █ 
▒██░   ▒██  ▀█▄  ▒██▒▓██  ▀█ ██▒░ ▓██▄   ▒▓█    ▄ ▒██  ▀█▄  ▓██  ▀█ ██▒
▒██░   ░██▄▄▄▄██ ░██░▓██▒  ▐▌██▒  ▒   ██▒▒▓▓▄ ▄██▒░██▄▄▄▄██ ▓██▒  ▐▌██▒
░██████▒▓█   ▓██▒░██░▒██░   ▓██░▒██████▒▒▒ ▓███▀ ░ ▓█   ▓██▒▒██░   ▓██░
░ ▒░▓  ░▒▒   ▓▒█░░▓  ░ ▒░   ▒ ▒ ▒ ▒▓▒ ▒ ░░ ░▒ ▒  ░ ▒▒   ▓▒█░░ ▒░   ▒ ▒ 
░ ░ ▒  ░ ▒   ▒▒ ░ ▒ ░░ ░░   ░ ▒░░ ░▒  ░ ░  ░  ▒     ▒   ▒▒ ░░ ░░   ░ ▒░
  ░ ░    ░   ▒    ▒ ░   ░   ░ ░ ░  ░  ░  ░          ░   ▒      ░   ░ ░ 
    ░  ░     ░  ░ ░           ░       ░  ░ ░            ░  ░         ░ 
                                         ░                             
Author: {AUTHOR}    Version: {VERSION}
[/cyan]'''

DEFAULT_TIMEOUT = 10.0  # 默认超时值
# 默认的请求头
DEFAULT_HEADERS = {
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/70.0.3538.77 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
              "application/signed-exchange;v=b3;q=0.9",
    "Referer": "https://fauux.neocities.org/",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,ko;q=0.6",
    "Connection": "close"
}


class LainScan:
    def __init__(self, scan_url, words_path, client_params,
                 sleep_time=None, extension='', custom_code=None, show_length=False):
        self.loop = asyncio.new_event_loop()
        self.words = None
        self.result_list = None
        self.scan_url = scan_url
        self.words_path = words_path
        self.extension = extension
        self.client_params = client_params
        self.sleep_time = sleep_time
        self.show_length = show_length
        self.custom_code = custom_code

        # 初始化输出表格
        self.console = Console()
        self.table = Table(show_header=True, header_style='bold magenta')
        self.table.add_column('URL')
        self.table.add_column('Code', justify='center')
        # 开启显示返回长度，添加 Length 栏
        if self.show_length: self.table.add_column('Length', justify='center')

    # 加载字典
    async def load_words(self):
        async with aiofiles.open(self.words_path, 'r') as f:
            lines = await f.readlines()
        self.words = [line.strip() for line in lines]

    # 单个扫描
    async def scan(self, word, client):
        url = f'{self.scan_url}{word}{self.extension}'
        # 默认使用 HEAD 方法
        if not self.show_length:
            async with client.head(url) as resp:
                status = resp.status
                return status,
        # 如果开启显示返回长度，使用 GET 方法
        else:
            async with client.get(url) as resp:
                status = resp.status
                length = len(await resp.text())
                return status, length

    # 带有时间间隔的批量扫描
    async def scan_wait(self):
        await self.load_words()
        result_list = []
        async with aiohttp.ClientSession(**self.client_params) as client:
            for word in self.words:
                result = await self.scan(word, client)
                result_list.append(result)
                await asyncio.sleep(self.sleep_time)
        return result_list

    # 并发的批量扫描
    async def scan_gather(self):
        await self.load_words()
        async with aiohttp.ClientSession(**self.client_params) as client:
            tasks = [self.scan(word, client) for word in self.words]
            result_list = await asyncio.gather(*tasks)
        return result_list

    # 执行扫描
    def run(self):
        if self.sleep_time:
            self.result_list = self.loop.run_until_complete(self.scan_wait())
        else:
            self.result_list = self.loop.run_until_complete(self.scan_gather())

    # 输出结果
    def print_result(self):
        self.console.print(BANNER)
        for index, result in enumerate(self.result_list):
            url = f'{self.scan_url}{self.words[index]}{self.extension}'
            code = result[0]  # result -> (status, length)
            match code:
                case 200:
                    code = f'[green]{code}[/green]'
                case 301 | 302:
                    code = f'[blue]{code}[/blue]'
                case 401 | 403:
                    code = f'[purple]{code}[/purple]'
                # case 404:
                #     code = f'[red]{code}[/red]'
                case code if code in self.custom_code:
                    code = f'[red]{code}[/red]'
                case _:  # 没有符合的状态码则跳过输出此结果
                    continue
            # 向表格添加数据
            if self.show_length:
                self.table.add_row(url, code, str(result[1]))
            else:
                self.table.add_row(url, code)
        self.console.print(self.table)


# 解析自定义请求头，并与默认请求头合并
def parse_headers(headers: list):
    custom_headers = {k: v for k, v in [header.split(':', 1) for header in headers]}
    return {**DEFAULT_HEADERS, **custom_headers}


@click.command()
@click.option('-U', '--url', 'scan_url', required=True, help='需要扫描的URL')
@click.option('-W', '--words', 'words_path', required=True, help='字典文件路径')
@click.option('-E', '--ext', 'extension', default='', help='后缀名，默认为空')
@click.option('-H', '--header', 'headers', multiple=True, help='自定义请求头')
@click.option('-T', '--timeout', 'timeout', type=float, default=DEFAULT_TIMEOUT, help='超时时间，包括建立连接到读取返回，单位：秒，默认：10.0')
@click.option('--redirect', 'redirect', is_flag=True, help='是否自动跳转，默认不跳转，开启后遇到 301 或 302 会返回跳转后的状态码')
@click.option('--sleep-time', 'sleep_time', type=float, help='请求间隔，开启后将不会并发执行，单位：秒')
@click.option('--custom-code', 'custom_code', type=int, multiple=True, help='自定义返回状态码，默认：200 301 302 401 403')
@click.option('--show-length', 'show_length', is_flag=True, help='是否显示返回长度，如果开启则使用 GET 方法替代 HEAD，且启用自动跳转')
def main(scan_url, words_path, headers, timeout, redirect, sleep_time, extension, custom_code, show_length):
    client_params = {
        'headers': parse_headers(headers),
        'requote_redirect_url': redirect,
        'timeout': aiohttp.ClientTimeout(total=timeout),
    }
    lain_scan = LainScan(scan_url, words_path, client_params, sleep_time, extension, custom_code, show_length)
    lain_scan.run()
    lain_scan.print_result()


if __name__ == '__main__':
    main()
