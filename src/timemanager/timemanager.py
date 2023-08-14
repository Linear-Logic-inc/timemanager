import time as time_module
from ctypes import windll
import numpy as np
import pandas as pd
import datetime
import jpholiday

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
    def __init__(self, date=None):
        #-----------------取引時間に関する関数群-----------------
        self.set_time_of_quotes(date=date)
        
    def set_time_of_quotes(self, date):
        if date is None:
            date = now().date()
        else:
            date = to_date(date)
            
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

    def is_lunch_break(self, time=None, inclusive=False):
        time = time or now()
        if inclusive:
            return (self.zenba_last <= time <= self.goba_first)
        else:
            return (self.zenba_last < time < self.goba_first)

    def is_before_start(self, time=None, inclusive=False):
        time = time or now()
        if inclusive:
            return (time <= self.zenba_first)
        else:
            return (time < self.zenba_first)

    def is_after_end(self, time=None, inclusive=False):
        time = time or now()
        if inclusive:
            return (self.goba_last <= time)
        else:
            return (self.goba_last < time)

    def is_trading_hours(self, time=None, inclusive=True):
        time = time or now()
        if inclusive:
            return (self.zenba_first <= time <= self.zenba_last) or (self.goba_first <= time <= self.goba_last)
        else:
            return (self.zenba_first < time < self.zenba_last) or (self.goba_first < time < self.goba_last)

    def is_last_five_minutes(self, time=None, inclusive=True):
        time = time or now()
        if inclusive:
            return (self.five_minutes_before_goba_last <= time <= self.goba_last)
        else:
            return (self.five_minutes_before_goba_last < time < self.goba_last)
    
    @staticmethod
    def settlement_date(trade_date):
        """約定日から受渡日を計算する"""
        trade_date = to_date(trade_date) 
        if trade_date < datetime.date(2019, 7, 16):
            delta = 3 # 2019年7月16日より前は4営業日目が受渡日
        else:
            delta = 2 # 2019年7月16日以降は3営業日目が受渡日
            
        res = trade_date
        for i in range(delta):
            res = TradeTime.next_business_day(res)
            
        return res
    
    @staticmethod
    def is_business_day(time_obj):
        """
        銀行カレンダーにおいて営業日か判定する
        
        Parameters
        ----------
        time_obj : datetime-like object
            datetime.datetime, datetime.date, numpy.datetime64, pd.Timestamp, str型など
            str型の場合はpd.Timestampを通して変換する
        
        Returns
        -------
        res : boolean
            営業日か。土日祝または12/31 ~ 01/03 ならばFalse、それ以外ならTrue
        """
        # datetime.date型に変換する
        date = to_date(time_obj)
        
        # 祝日かどうかを判定
        if jpholiday.is_holiday(date):
            return False

        # 土曜日かどうかを判定
        if date.weekday() == 5:
            return False

        # 日曜日かどうかを判定
        if date.weekday() == 6:
            return False

        # 12月31日から1月3日までの期間は休みと判定
        if date.month == 12 and date.day >= 31:
            return False
        if date.month == 1 and date.day <= 3:
            return False

        # 上記条件に当てはまらなければ営業日と判定
        return True
    
    @staticmethod
    def next_business_day(time_obj, include_now=False):
        """
        銀行カレンダーにおける次の営業日を返す。
        
        Parameters
        ----------
        time_obj : datetime-like object
            datetime.datetime, datetime.date, numpy.datetime64, pd.Timestamp, str型など
            str型の場合はpd.Timestampを通して変換する
            
        include_now : bool, default: True
            if True, 入力が営業日ならそのまま返す。
            if False, 前日以降で最も近い営業日を返す
        
        Returns
        -------
        res : datetime.date object
            次の営業日。
        """
        date = to_date(time_obj)
        if not include_now:
            date = next_day(date)
            
        while not TradeTime.is_business_day(date):
            date = next_day(date)
        return date
    
    @staticmethod
    def previous_business_day(time_obj, include_now=False):
        """
        銀行カレンダーにおける前の営業日を返す。
        
        Parameters
        ----------
        time_obj : datetime-like object
            datetime.datetime, datetime.date, numpy.datetime64, pd.Timestamp, str型など
            str型の場合はpd.Timestampを通して変換する
            
        include_now : bool, default: True
            if True, 入力が営業日ならそのまま返す。
            if False, 前日以前で最も近い営業日を返す
        
        Returns
        -------
        res : datetime.date object
            前の営業日。
        """
        date = to_date(time_obj)
        if not include_now:
            date = previous_day(date)
            
        while not TradeTime.is_business_day(date):
            date = previous_day(date)
        return date

trade_time = TradeTime()


class TimeRange:
    def __init__(self, start, end):
        """
        連続した時間範囲[start, end)を扱う
        numpy.datetime64がベースで、timezoneには非対応
        """
        self.start = np.datetime64(start)
        self.end = np.datetime64(end)
        if self.start >= self.end:
            raise ValueError("End time must be after start time")

    def __str__(self):
        return f"TimeRange('{self.start}', '{self.end}')"

    def __repr__(self):
        return self.__str__()

    def duration(self):
        return self.end - self.start

    def contains(self, timestamp):
        return self.start <= np.datetime64(timestamp) < self.end

    def overlaps(self, other_range):
        """
        2つのTimeRangeが重なっているか/もしくは連続しているかを調べる
        片方のendともう片方のstartが同じ場合はTrueを返す
        """
        return self.start <= other_range.end and self.end >= other_range.start

    def intersection(self, other_range):
        """2つのTimeRangeの共通範囲を返す"""
        if not self.overlaps(other_range):
            return None
        return TimeRange(max(self.start, other_range.start), min(self.end, other_range.end))

    def union(self, other_range):
        """どちらかのTimeRangeに含まれる範囲を返す"""
        return TimeRange(min(self.start, other_range.start), max(self.end, other_range.end))

    def copy(self):
        return TimeRange(self.start, self.end)
    
    def arange(self, unit='D'):
        """
        時間範囲に含まれる時刻をnumpy.array形式で返す
        unitはnumpy.datetime64準拠
        """
        np_time_units = {'Y','M','W','D','h','m','s','us','ns','ps','fs','as'}
        assert unit in np_time_units

        time_start = self.start.astype(f'datetime64[{unit}]')
        time_stop = self.end.astype(f'datetime64[{unit}]') + np.timedelta64(1, unit)

        return np.arange(time_start, time_stop, np.timedelta64(1, unit))
    
    def __sub__(self, other):
        if isinstance(other, TimeRange):
            if intersection := self.intersection(other):
                ranges = []
                if self.start < intersection.start:
                    ranges.append(TimeRange(self.start, intersection.start))
                if self.end > intersection.end:
                    ranges.append(TimeRange(intersection.end, self.end))
                return ranges
            else:
                return [self]
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, TimeRange):
            if self.overlaps(other):
                return self.union(other)
            else:
                raise ValueError("Ranges do not overlap")
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, TimeRange):
            return other.intersection(self)
        return NotImplemented

class DisjointTimeRanges:
    def __init__(self, ranges=None):
        """
        時間範囲(=連続した時間範囲の集合)を扱う
        numpy.datetime64がベースで、timezoneには非対応
        """
        self.ranges = ranges if ranges else []

    def add_range(self, start, end):
        """"時間範囲に[start, end)を追加する"""
        new_range = TimeRange(start, end)

        for existing_range in self.ranges:
            if existing_range.overlaps(new_range):
                new_range = TimeRange(min(existing_range.start, new_range.start), max(existing_range.end, new_range.end))
                self.ranges.remove(existing_range)

        self.ranges.append(new_range)

    def get_ranges(self):
        return self.ranges
    
    def __repr__(self):
        return f"DisjointTimeRanges({repr(self.ranges)})"

    def __add__(self, other):
        if isinstance(other, TimeRange):
            new_ranges = DisjointTimeRanges(self.ranges.copy())
            new_ranges.add_range(other.start, other.end)
            return new_ranges
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, TimeRange):
            new_ranges = DisjointTimeRanges(
                sum([existing_range - other for existing_range in self.ranges], [])
            )
            return new_ranges
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, TimeRange):
            new_ranges = DisjointTimeRanges([other.copy()])
            for existing_range in self.ranges:
                new_ranges -= existing_range
            return new_ranges
        return NotImplemented