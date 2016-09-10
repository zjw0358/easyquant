# coding: utf-8
"""
演示如何进行单元测试
"""
import time
import unittest
from unittest import mock
import datetime
import pandas as pd
from easyquant.easydealutils.time import get_next_trade_date, is_trade_date
import arrow

from dateutil import tz
from easyquant.main_engine import MainEngine
from easyquant.push_engine.clock_engine import ClockEngine, ClockMomentHandler
from easyquant.event_engine import EventEngine

__author__ = 'Shawn'

# 需要制定一个有效的证券账户信息
main_engine = MainEngine('ht', "tmp/ht.json")


class BaseTest(unittest.TestCase):
    """
    基础的配置
    """

    @property
    def main_engine(self):
        return main_engine

    @property
    def clock_engine(self):
        """
        :return:
        """
        return self.main_engine.clock_engine


class TestClock(BaseTest):
    """
    时钟的单元测试
    """

    @property
    def main_engine(self):
        return self._main_engine

    def setUp(self):
        """
        执行每个单元测试 前 都要执行的逻辑
        :return:
        """
        # 设定下一个交易日
        self.trade_date = get_next_trade_date(datetime.date.today() - datetime.timedelta(days=1))

        self.time = datetime.time(0, 0, 0, tzinfo=tz.tzlocal())

        now = datetime.datetime.combine(self.trade_date, self.time)
        # 此处重新定义 main_engine
        self._main_engine = MainEngine('ht', 'tmp/ht.json')

        # 设置为不在交易中
        self.clock_engine.trading_state = False

        # 时钟事件计数
        self.counts = {
            0.5: [],
            1: [],
            5: [],
            15: [],
            30: [],
            60: [],
            "open": [],
            "pause": [],
            "continue": [],
            "close": [],

        }

    def tearDown(self):
        """
        执行每个单元测试 后 都要执行的逻辑
        :return:
        """

    def test_set_now(self):
        """
        1. 重设 clock_engine 的时间
        2. 通过 mock 来重设时间戳
        3. mock 只能重设 time.time 函数的时间戳,但是不能重设 datetime.datetime.now 函数的时间戳,详情见: http://stackoverflow.com/questions/4481954/python-trying-to-mock-datetime-date-today-but-not-working
        4. 在代码中需要使用时间戳时,请通过 clock_engine 中的 now 或者 now_dt 接口获得,也可以使用 time.time 获得.否则该段代码将不适用于需要更改时间戳的单元测试
        :return:
        """
        tzinfo = tz.tzlocal()
        # 使用datetime 类构建时间戳
        now = datetime.datetime(2016, 7, 14, 8, 59, 50, tzinfo=tzinfo)

        # 通过mock ,将 time.time() 函数的返回值重设为上面的打算模拟的值,注意要转化为浮点数时间戳
        time.time = mock.Mock(return_value=now.timestamp())

        # 生成一个时钟引擎
        clock_engien = ClockEngine(EventEngine(), tzinfo)

        # 去掉微秒误差后验证其数值
        self.assertEqual(clock_engien.now, now.timestamp())  # time.time 时间戳
        self.assertEqual(clock_engien.now_dt, now)  # datetime 时间戳

        # 据此可以模拟一段时间内各个闹钟事件的触发,比如模拟开市9:00一直到休市15:00
        for _ in range(60):
            clock_engien.tock()
            now += datetime.timedelta(seconds=1)  # 每秒触发一次 tick_tock
            time.time = mock.Mock(return_value=now.timestamp())
            self.assertEqual(clock_engien.now, now.timestamp())  # time.time 时间戳
            self.assertEqual(clock_engien.now_dt, now)  # datetime 时间戳

    def test_clock_moment_is_active(self):
        # 设置时间
        now = datetime.datetime.combine(
            self.trade_date,
            datetime.time(23, 59, 58, tzinfo=tz.tzlocal()),
        )
        time.time = mock.Mock(return_value=now.timestamp())

        # 触发前, 注册时间事件
        moment = datetime.time(23, 59, 59, tzinfo=tz.tzlocal())
        cmh = ClockMomentHandler(self.clock_engine, 'test', moment)
        # 确认未触发
        self.assertFalse(cmh.is_active())

        # 将系统时间设置为触发时间
        now = datetime.datetime.combine(
            self.trade_date,
            datetime.time(23, 59, 59, tzinfo=tz.tzlocal())
        )
        time.time = mock.Mock(return_value=now.timestamp())

        # 确认触发
        self.assertTrue(cmh.is_active())

    def test_clock_update_next_time(self):
        # 设置时间
        now = datetime.datetime.combine(
            self.trade_date,
            datetime.time(23, 59, 58, tzinfo=tz.tzlocal())
        )
        time.time = mock.Mock(return_value=now.timestamp())

        # 触发前, 注册时间事件
        moment = datetime.time(23, 59, 59, tzinfo=tz.tzlocal())
        cmh = ClockMomentHandler(self.clock_engine, 'test', moment)
        # 确认未触发
        self.assertFalse(cmh.is_active())

        # 将系统时间设置为触发时间
        now = datetime.datetime.combine(
            self.trade_date,
            datetime.time(23, 59, 59, tzinfo=tz.tzlocal())
        )
        time.time = mock.Mock(return_value=now.timestamp())

        # 确认触发
        self.assertTrue(cmh.is_active())

        # 更新下次触发时间
        cmh.update_next_time()
        # 确认未触发
        self.assertFalse(cmh.is_active())

    def test_register_clock_moment_makeup(self):
        # 测试补发
        self.register_clock_moent_makeup(True)

    def test_register_clock_moment_not_makeup(self):
        # 测试不补发
        self.register_clock_moent_makeup(False)

    def register_clock_moent_makeup(self, makeup):
        begin = datetime.datetime.combine(
            self.trade_date,
            datetime.time(23, 59, 59, tzinfo=tz.tzlocal())
        )
        time.time = mock.Mock(return_value=begin.timestamp())

        # 注册时刻一个超时事件
        moment = datetime.time(0, 0, 0, tzinfo=tz.tzlocal())
        self.clock_engine.register_moment('test', moment, makeup=makeup)

        self.test_active = False

        def clock(event):
            # 记录补发
            if event.data.clock_event == 'test':
                self.test_active = True

        self.main_engine.event_engine.register(ClockEngine.EventType, clock)

        # 开启事件引擎
        self.main_engine.event_engine.start()
        self.clock_engine.tock()

        time.sleep(0.1)
        self.main_engine.event_engine.stop()

        # 确认补发
        self.assertEqual(self.test_active, makeup)

    def test_register_clock_interval_trading_true(self):
        # 交易触发, 交易阶段
        trading = True
        begin = datetime.datetime.combine(
            self.trade_date,
            datetime.time(9, 15, 0, tzinfo=tz.tzlocal())
        )
        # 确认在交易中
        self.register_clock_interval(begin, trading, 1)
        self.assertTrue(self.clock_engine.trading_state)

    def test_register_clock_interval_not_trading_true(self):
        # 交易触发, 非交易阶段
        trading = True
        begin = datetime.datetime.combine(
            self.trade_date,
            datetime.time(15, 15, 0, tzinfo=tz.tzlocal())
        )
        # 确认在交易中
        self.register_clock_interval(begin, trading, 0)
        self.assertFalse(self.clock_engine.trading_state)

    def test_register_clock_interval_trading_false(self):
        # 非交易触发, 交易阶段
        trading = False
        begin = datetime.datetime.combine(
            self.trade_date,
            datetime.time(9, 15, 0, tzinfo=tz.tzlocal())
        )
        # 确认在交易中
        self.register_clock_interval(begin, trading, 1)
        self.assertTrue(self.clock_engine.trading_state)

    def test_register_clock_interval_not_trading_false(self):
        # 非交易触发, 非交易阶段
        trading = False
        begin = datetime.datetime.combine(
            self.trade_date,
            datetime.time(15, 15, 0, tzinfo=tz.tzlocal())
        )
        # 确认在交易中
        self.register_clock_interval(begin, trading, 1)
        self.assertFalse(self.clock_engine.trading_state)

    def register_clock_interval(self, begin, trading, active_times):
        time.time = mock.Mock(return_value=begin.timestamp())
        self.active_times = 0

        def clock(event):
            # 记录补发
            if event.data.clock_event == clock_type:
                self.active_times += 1

        self.main_engine.event_engine.register(ClockEngine.EventType, clock)

        self.main_engine.event_engine.start()
        self.clock_engine.tock()

        clock_type = minute_interval = 2.5
        # 注册事件
        handler = self.clock_engine.register_interval(minute_interval, trading)
        # 确定已经添加到列表
        self.assertIn(handler, self.clock_engine.clock_interval_handlers)

        # 开启事件引擎
        for sec in range(int(minute_interval * 60)):
            now = begin + datetime.timedelta(seconds=sec)
            time.time = mock.Mock(return_value=now.timestamp())
            self.clock_engine.tock()
        time.sleep(1)
        self.main_engine.event_engine.stop()

        self.assertEqual(self.active_times, active_times)

    def test_tick_interval_event(self):
        """
        测试 tick 中的时间间隔事件
        时间间隔事件
        从开始前1分钟一直到收市后1分钟, 触发所有的已定义时钟事件
        :return:
        """
        # 各个时间间隔的触发次数计数
        counts = self.counts

        def count(event):
            # 时钟引擎必定在上述的类型中
            self.assertIn(event.data.clock_event, counts)
            # 计数
            counts[event.data.clock_event].append(self.clock_engine.now_dt)

        # 注册一个响应时钟事件的函数
        self.main_engine.event_engine.register(ClockEngine.EventType, count)

        # 开启事件引擎
        self.main_engine.event_engine.start()

        # 模拟从开市前1分钟, 即8:59分, 到休市后1分钟的每秒传入时钟接口
        begin = datetime.datetime.combine(
            self.trade_date,
            datetime.time(8, 59, tzinfo=self.clock_engine.tzinfo)
        )
        hours = 15 - 9
        mins = hours * 60 + 2
        seconds = 60 * mins
        for secs in range(seconds):
            now = begin + datetime.timedelta(seconds=secs)
            time.time = mock.Mock(return_value=now.timestamp())
            self.clock_engine.tock()
            time.sleep(0.001)

        # 等待事件引擎处理
        self.main_engine.event_engine.stop()

        # 核对次数, 休市的时候不会统计
        self.assertEqual(len(counts[60]), 15 - 9 + 1 - len(["9:00"]))
        self.assertEqual(len(counts[30]), (15 - 9) * 2 + 1 - len(["9:00"]))
        self.assertEqual(len(counts[15]), (15 - 9) * 4 + 1 -
                         len(["9:00"]))

    def test_tick_moment_event(self):
        """
        测试 tick 中的时刻时钟事件
        时间间隔事件
        每隔25分钟触发一次,连续进行8天
        :return:
        """
        # 各个时间间隔的触发次数计数
        counts = self.counts
        days = 8
        interval = datetime.timedelta(minutes=25)

        def count(event):
            # 时钟引擎必定在上述的类型中
            self.assertIn(event.data.clock_event, counts)
            # 计数
            counts[event.data.clock_event].append(self.clock_engine.now_dt)

        # 从 self.trade_date 的零点开始
        begin = datetime.datetime.combine(
            self.trade_date,
            datetime.time(0, 0, tzinfo=self.clock_engine.tzinfo)
        )
        # 结束时间为8天后的23:59:59
        end = (begin + datetime.timedelta(days=days)).replace(hour=23, minute=59, second=59)

        # 重置时间到凌晨
        time.time = mock.Mock(return_value=begin.timestamp())

        # 预估时间事件触发次数, 每个交易日触发一次
        actived_times = 0
        for date in pd.date_range(begin.date(), periods=days + 1):
            if is_trade_date(date):
                actived_times += 1

        # 注册一个响应时钟事件的函数
        self.main_engine.event_engine.register(ClockEngine.EventType, count)

        # 开启事件引擎
        self.main_engine.event_engine.start()

        now = begin
        while 1:
            time.time = mock.Mock(return_value=now.timestamp())
            self.clock_engine.tock()
            time.sleep(0.001)
            now += interval
            if now >= end:
                break

        # 等待事件引擎处理
        self.main_engine.event_engine.stop()
        print({k: len(v) for k, v in counts.items() if isinstance(k, str)})
        # 开盘收盘, 中午开盘休盘, 必定会触发1次
        self.assertEqual(len(counts['open']), actived_times)
        self.assertEqual(len(counts['pause']), actived_times)
        self.assertEqual(len(counts['continue']), actived_times)
        self.assertEqual(len(counts['close']), actived_times)
