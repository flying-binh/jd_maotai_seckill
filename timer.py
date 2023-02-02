# -*- coding:utf-8 -*-
import time
import requests
import json

from datetime import datetime
from jd_logger import logger
from config import global_config
from util import (
    parse_json
)

class Timer(object):
    def __init__(self, sleep_interval=0.5):
        # '2018-09-28 22:45:50.000'
        # buy_time = 2020-12-22 09:59:59.500
        localtime = time.localtime(time.time())

        self.sku_id = global_config.getRaw('config', 'sku_id')

        yushou_info = self.jd_yushou_time_info()

        #
        '''
        注释掉了原来从配置获取抢购时间和预购时间
        buy_time_everyday = global_config.getRaw('config', 'buy_time').__str__()
        self.buy_time = datetime.strptime(
            localtime.tm_year.__str__() + '-' + localtime.tm_mon.__str__() + '-' + localtime.tm_mday.__str__()
            + ' ' + buy_time_everyday,"%Y-%m-%d %H:%M:%S.%f")
        '''
        self.buy_time = datetime.strptime(yushou_info.get('qiangStime'), "%Y-%m-%d %H:%M:%S")
        self.buy_time_ms = int(time.mktime(self.buy_time.timetuple()) * 1000.0 + self.buy_time.microsecond / 1000)

        '''
        reserve_time_everyday = global_config.getRaw('config', 'reserve_time').__str__()
        self.reserve_time = datetime.strptime(
            localtime.tm_year.__str__() + '-' + localtime.tm_mon.__str__() + '-' + localtime.tm_mday.__str__()
            + ' ' + reserve_time_everyday,
            "%Y-%m-%d %H:%M:%S.%f")
        '''
        self.reserve_time = datetime.strptime(yushou_info.get('yueStime'), "%Y-%m-%d %H:%M:%S")
        self.reserve_time_ms = int(time.mktime(self.reserve_time.timetuple()) * 1000.0 + self.reserve_time.microsecond / 1000)
        self.reserve_end_time = datetime.strptime(yushou_info.get('yueEtime'), "%Y-%m-%d %H:%M:%S")
        self.reserve_end_time_ms = int(time.mktime(self.reserve_end_time.timetuple()) * 1000.0 + self.reserve_end_time.microsecond / 1000)

        self.sleep_interval = sleep_interval
        self.diff_time = self.local_jd_time_diff()
        self.yushou_url = "https:{}".format(yushou_info.get('url'))

    def jd_time(self):
        """
        从京东服务器获取时间毫秒
        :return:
        """
        url = "https://api.m.jd.com/client.action?functionId=queryMaterialProducts&client=wh5"
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36'}
        ret = requests.get(url=url, headers=headers).text
        logger.info('服务器时间:{}'.format(ret))
        js = json.loads(ret)
        return int(js["currentTime2"])

    def jd_yushou_time_info(self):
        '''
        从京东服务器获取预购时间，抢购时间
        '''
        url = 'https://yushou.jd.com/youshouinfo.action?'
        payload = {
            'callback': 'fetchJSON',
            'sku': self.sku_id,
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': global_config.getRaw('config', 'DEFAULT_USER_AGENT'),
            'Referer': 'https://item.jd.com/{}.html'.format(self.sku_id),
        }
        resp = requests.get(url=url, params=payload, headers=headers)
        logger.info('response of youshouinfo {}'.format(resp.text))
        resp_json = parse_json(resp.text)
        return resp_json

    def local_time(self):
        """
        获取本地毫秒时间
        :return:
        """
        return int(round(time.time() * 1000))

    def local_jd_time_diff(self):
        """
        计算本地与京东服务器时间差
        :return:
        """
        return self.local_time() - self.jd_time()
        #return self.local_time() - self.local_time()

    def start_buy(self):
        logger.info('正在等待到达设定时间:{}，检测本地时间与京东服务器时间误差为【{}】毫秒'.format(self.buy_time, self.diff_time))
        while True:
            # 本地时间减去与京东的时间差，能够将时间误差提升到0.1秒附近
            # 具体精度依赖获取京东服务器时间的网络时间损耗
            if self.local_time() - self.diff_time >= self.buy_time_ms:
                logger.info('时间到达，开始执行抢购……')
                break
            else:
                time.sleep(self.sleep_interval)

    def start_reserve(self):
        logger.info('正在等待到达设定时间:{}，检测本地时间与京东服务器时间误差为【{}】毫秒'.format(self.reserve_time, self.diff_time))
        while True:
            # 本地时间减去与京东的时间差，能够将时间误差提升到0.1秒附近
            # 具体精度依赖获取京东服务器时间的网络时间损耗
            if self.local_time() - self.diff_time > self.reserve_end_time_ms:
                logger.info('预约已经结束，请下次再来！')
            elif self.local_time() - self.diff_time >= self.reserve_time_ms:
                logger.info('时间到达，开始执行预约......')
                break
            else:
                logger.info('时间尚未开始，请稍等...')
                time.sleep(self.sleep_interval)