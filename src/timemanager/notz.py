import time as time_module
import datetime

import numpy as np
import pandas as pd
import jpholiday

from .common import *

TIMEZONE = pd.Timedelta(9, 'h')

# windowsのクロック解像度はデフォルトでは1/64秒=15.625ミリ秒
# これをより短く設定する
DTIME = 1

try:
    from ctypes import windll
except ImportError as e:
    # LINUX等のとき
    WINDOWS=False
else:
    WINDOWS=True
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
        if WINDOWS:
            # クロック解像度の変更をもとに戻す
            windll.winmm.timeEndPeriod(DTIME)

_DO_NOT_REFER_THIS = _HiddenDestructor()

def now():
    """現在時刻をpandas.Timestamp型で返す"""
    return pd.Timestamp('now')

def from_utc(time):
    """UTC時刻をpandas.Timestamp型に変換する"""
    return pd.Timestamp(time) + TIMEZONE

def from_timezone(time):
    """Timezoneに応じた時刻をpandas.Timestamp型に変換する"""
    return pd.Timestamp(time).tz_localize(None)

def to_datetime(time_obj):  
    if isinstance(time_obj, datetime.datetime):
        return time_obj
    elif isinstance(time_obj, datetime.date):
        return datetime.datetime(time_obj.year, time_obj.month, time_obj.day)
    elif isinstance(time_obj, np.datetime64):
        return pd.Timestamp(time_obj).to_pydatetime(warn=False)
    elif isinstance(time_obj, pd.Timestamp):
        return time_obj.to_pydatetime(warn=False)
    elif isinstance(time_obj, str): 
        if time_obj == 'now':
            return now().to_pydatetime(warn=False)
        else:
            return pd.to_datetime(time_obj).to_pydatetime(warn=False)
    else:
        raise ValueError("Unsupported type")
        
def to_date(time_obj):
    return to_datetime(time_obj).date()
    
def wait(seconds):
    """
    プログラムを指定秒数停止させる。
    """
    if seconds > 0:
        time_module.sleep(seconds)

def wait_until(end_time):
    """
    プログラムを指定時刻まで停止させる。

    Parameters
    ----------
    end_time: pandas.Timestamp or numpy.datetime64
        プログラムを再開させる(当該タイムゾーンでの)時刻
        utcのnumpy.datetime64, utcのpandas.Timestamp, timezone付きのpandas.Timestampのいずれか
    """
    end_time = pd.Timestamp(end_time)
    wait((end_time - now()).total_seconds())

def wait_if_pace_too_fast(dtime_second = 1):
    """
    前回にこの関数を呼び出したときから指定時間以上経過していなければ、
    指定時間経過するまで待つ
    """
    global _time_last_wait_if_func_called
    
    if not _time_last_wait_if_func_called is None:
        end_time = _time_last_wait_if_func_called + pd.to_timedelta(dtime_second, unit='s')
        wait_until(end_time)
    _time_last_wait_if_func_called = now()

def time2int(t):
    if isinstance(t, pd.Timestamp):
        t = t.to_numpy().astype('datetime64[ns]')
    elif isinstance(t, np.datetime64):
        t = t.astype('datetime64[ns]')
    elif t == 'now':
        t = now().to_numpy().astype('datetime64[ns]')
    else:
        t = np.datetime64(t, 'ns')
    return int.from_bytes(t.tobytes(), byteorder='big')

def int2time(n):
    t = np.frombuffer(n.to_bytes(8, byteorder='big'), dtype='datetime64[ns]')[0]
    return pd.Timestamp(t)

trade_time = create_trade_time_obj(to_date=to_date, TIMEZONE=None, now=now)
