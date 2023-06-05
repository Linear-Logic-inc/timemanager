import time as time_module
from ctypes import windll
import numpy as np
import pandas as pd
import datetime

# タイムゾーンの設定
TIMEZONE = 'Asia/Tokyo'

# windowsのクロック解像度はデフォルトでは1/64秒=15.625ミリ秒
# これをより短く設定する
DTIME = 1
windll.winmm.timeBeginPeriod(DTIME)

# wait_if_pace_too_fast 関数が最後に呼ばれた時刻
_time_last_wait_if_func_called = None

# モジュールの削除と同時にクロックの解像度の変更をもとに戻す必要があるが、
# モジュールにデストラクタを定義する方法がわからないので、
# このモジュールでしか使われない適当なクラスのインスタンスを作って、
# そこのデストラクタに解像度を元に戻す処理を書く
class _HiddenDestructor:
    def __init__(self):
        pass
    
    def __del__(self):
        # クロック解像度の変更をもとに戻す
        windll.winmm.timeEndPeriod(DTIME)

_DO_NOT_REFER_THIS = _HiddenDestructor()

def now():
    """現在時刻をpandas.Timestamp型で返す"""
    return pd.to_datetime('now', utc=True).tz_convert(TIMEZONE)

def from_utc(time):
    """UTC時刻をpandas.Timestamp型に変換する"""
    return pd.to_datetime(time, utc=True).tz_convert(TIMEZONE)

def from_timezone(time, timezone=None):
    """
    任意のタイムゾーンの時刻をpandas.Timestamp型に変換する
    
    Parameters
    ----------
    time : str or datetime-like object
        時刻。
    timezone : str, optional
        タイムゾーン。デフォルトではAsia/Tokyo(UTC+9)として処理される。
    """
    if hasattr(time, 'tzinfo') and time.tzinfo is not None:
        # すでにタイムゾーンの情報があるオブジェクトのとき
        return pd.to_datetime(time).tz_convert(TIMEZONE)
    if timezone is None:
        return pd.to_datetime(time, utc=False).tz_localize(TIMEZONE)
    else:
        return pd.to_datetime(time, utc=False).tz_localize(timezone).tz_convert(TIMEZONE)

def to_datetime(time_obj):    
    if isinstance(time_obj, datetime.datetime):
        return time_obj
    elif isinstance(time_obj, datetime.date):
        return datetime.datetime(time_obj.year, time_obj.month, time_obj.day)
    elif isinstance(time_obj, np.datetime64):
        return pd.Timestamp(time_obj).to_pydatetime()
    elif isinstance(time_obj, pd.Timestamp):
        return time_obj.to_pydatetime()
    elif isinstance(time_obj, str):
        return pd.to_datetime(time_obj).to_pydatetime()
    else:
        raise ValueError("Unsupported type")
        
def to_date(time_obj):
    return to_datetime(time_obj).date()
    
def previous_day(date):
    return date - datetime.timedelta(days=1)
    
def next_day(date):
    return date + datetime.timedelta(days=1)
    
def wait(seconds):
    """
    プログラムを指定秒数停止させる。
    """
    if seconds > 0:
        time_module.sleep(seconds)

def wait_until(utc_end_time):
    """
    プログラムを指定時刻まで停止させる。

    Parameters
    ----------
    utc_end_time: pandas.Timestamp or numpy.datetime64
        プログラムを再開させる時刻
        utcのnumpy.datetime64, utcのpandas.Timestamp, timezone付きのpandas.Timestampのいずれか
    """
    end_time = pd.to_datetime(utc_end_time, utc=True).tz_convert(TIMEZONE)
    wait((end_time - now()).total_seconds())

def wait_if_pace_too_fast(dtime_second = 1):
    """
    前回にこの関数を呼び出したときから指定時間以上経過していなければ、
    指定時間経過するまで待つ
    """
    global _time_last_wait_if_func_called
    
    if not _time_last_wait_if_func_called is None:
        end_time = _time_last_wait_if_func_called + pd.to_timedelta(dtime_second, unit='S')
        wait_until(end_time)
    _time_last_wait_if_func_called = now()

def time2int(t):
    if isinstance(t, pd.Timestamp):
        t = t.to_numpy().astype('datetime64[ns]')
    elif isinstance(t, np.datetime64):
        t = t.astype('datetime64[ns]')
    elif t == 'now':
        t = self.now().to_numpy().astype('datetime64[ns]')
    else:
        t = np.datetime64(t, 'ns')
    return int.from_bytes(t.tobytes(), byteorder='big')

def int2time(n):
    utc_time = np.frombuffer(n.to_bytes(8, byteorder='big'), dtype='datetime64[ns]')[0]
    return pd.to_datetime(utc_time, utc=True).tz_convert(TIMEZONE)

class TradeTime:
    def __init__(self):
        #-----------------取引時間に関する関数群-----------------
        self.set_time_of_quotes()
        
    def set_time_of_quotes(self):
        date = now().date()
        if ('date' not in dir(self)) or (date != self.date):
            # この関数を初めて呼び出すか、
            # 前回呼び出した時から日付が変わっていた時
            date_args = {
                "year": date.year, 
                "month": date.month, 
                "day": date.day, 
                "tz": TIMEZONE,
            }
            self.zenba_first = pd.Timestamp(**date_args, hour=9, minute=0)
            self.zenba_last = pd.Timestamp(**date_args, hour=11, minute=30)
            self.goba_first = pd.Timestamp(**date_args, hour=12, minute=30)
            self.goba_last = pd.Timestamp(**date_args, hour=15, minute=0)
            self.five_minutes_before_goba_last = pd.Timestamp(**date_args, hour=14, minute=55)

            self.date = date

    def is_lunch_break(self):
        self.set_time_of_quotes()
        return (self.zenba_last < now() < self.goba_first)

    def is_before_start(self):
        self.set_time_of_quotes()
        return (now() < self.zenba_first)

    def is_after_end(self):
        self.set_time_of_quotes()
        return (self.goba_last < now())

    def is_trading_hours(self):
        self.set_time_of_quotes()
        _now = now()
        return (self.zenba_first <= _now <= self.zenba_last) or (self.goba_first <= _now <= self.goba_last)

    def is_last_five_minutes(self):
        self.set_time_of_quotes()
        return (self.five_minutes_before_goba_last <= now() <= self.goba_last)

trade_time = TradeTime()