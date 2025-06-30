from functools import total_ordering
import datetime

import numpy as np
import pandas as pd
from sortedcontainers import SortedDict
import jpholiday

@total_ordering
class TimewithInf:
    """
    A class to represent time with support for positive and negative infinity.
    
    Attributes
    ----------
    is_inf : bool
        True if the value is positive infinity, False otherwise.
    is_ninf : bool
        True if the value is negative infinity, False otherwise.
    value : np.datetime64 or float
        The actual value of the object. Could be a datetime or infinity.
        
    Methods
    -------
    time_or_none()
        Returns the time value or None if the value is infinity.
    __str__()
        Return a formatted string representation of the object.
    __repr__()
        Return the official string representation of the object.
    __eq__(other)
        Check the equality of this object with another TimewithInf object.
    __lt__(other)
        Compare this object with another TimewithInf object for ordering.
    """
    def __init__(self, value):
        """
        Initialize the TimewithInf object.
        
        Parameters
        ----------
        value : float or date-like string
            The value to be stored in the object. 
            Could be a datetime, np.inf, or -np.inf.
        """
        self.is_inf = False
        self.is_ninf = False
        
        if isinstance(value, float):
            assert value in [np.inf, -np.inf]
            if value == np.inf:
                self.is_inf = True
            elif value == (-np.inf):
                self.is_ninf = True
                
            self.value = value
        else:
            self.value = np.datetime64(value)
            
    def time_or_none(self):
        """
        Get the time value or None.
        
        Returns
        -------
        np.datetime64 or None
            Returns the time value or None if the value is infinity.
        """
        if self.is_inf or self.is_ninf:
            return None
        else:
            return self.value
        
    def __str__(self):
        return f"TimewithInf({self.value})"
    
    def __repr__(self):
        return str(self)
        
    def __eq__(self, other):
        if not isinstance(other, TimewithInf):
            other = TimewithInf(other)
            
        if type(self.value) == type(other.value):
            return self.value == other.value
        else:
            return False
        
    def __lt__(self, other):
        """return self < other"""
        if not isinstance(other, TimewithInf):
            other = TimewithInf(other)
            
        if self.is_inf:
            return False # (inf < other) ... False 
        elif self.is_ninf:
            if other.is_ninf:
                return False # (-inf < -inf) ... False
            else:
                return True # (-inf < other) ... True
        else:
            if other.is_ninf:
                return False # (self < -inf) ... False
            elif other.is_inf:
                return True # (self < inf) ... True
            else:
                return self.value < other.value
            
class TimeRange:
    """
    Represents a continuous time range [start, end).

    Attributes
    ----------
    start : np.datetime64 or None
        Starting point of the time range.
    end : np.datetime64 or None
        Ending point of the time range.
    is_duration_zero : bool
        True if the time range has zero duration.
    is_duration_inf : bool
        True if the time range has infinite duration.
    ranges : list
        A list containing this time range.

    Methods
    -------
    zero_range()
        Create a zero-duration time range.
    copy()
        Create a copy of this time range.
    duration()
        Get the duration of this time range.
    contains(t)
        Check whether a time value is contained within this time range.
    overlaps(other)
        Check whether this time range overlaps with another time range.
    continuous(other)
        Check whether this time range is continuous with another time range.
    intersection(other)
        Get the intersection of this time range with another.
    union(other)
        Get the union of this time range with another.
    to_array(unit='D')
        Get an array representation of this time range.
    shift(dtime)
        Shift this time range by a certain duration.
    __sub__(other)
        Subtract another time range from this time range.
    __or__(other)
        Get the union of this time range with another using the | operator.
    __and__(other)
        Get the intersection of this time range with another using the & operator.
    __xor__(other)
        Get the symmetric difference of this time range with another using the ^ operator.
    """
    def __init__(self, start=None, end=None):

        """
        Initialize a TimeRange object.
        
        Parameters
        ----------
        start : compatible with np.datetime64, optional
            Starting time of the range. If None, the range extends infinitely
            into the past.
        end : compatible with np.datetime64, optional
            Ending time of the range. If None, the range extends infinitely
            into the future.
        """
        if isinstance(start, TimewithInf):
            self.start = start.time_or_none()
            self._start_obj = start
        else:
            self.start = start and np.datetime64(start)
            self._start_obj = TimewithInf(start or (-np.inf))
            
        if isinstance(end, TimewithInf):
            self.end = end.time_or_none()
            self._end_obj = end
        else:
            self.end = end and np.datetime64(end)
            self._end_obj = TimewithInf(end or np.inf)
        
        self.is_duration_zero = self.start and self.end and (self.start >= self.end)
        self.is_duration_inf = (self.start is None) or (self.end is None)
        
        self.ranges = [self]
        
    @staticmethod
    def zero_range():
        """
        Returns
        -------
        TimeRange
            A time range object representing a zero-duration range.
        """
        return TimeRange('2020-01-01', '2020-01-01')
    
    def __str__(self):
        if self.is_duration_zero:
            return "TimeRange()"
        else:
            return f"TimeRange('{self.start}', '{self.end}')"

    def __repr__(self):
        return self.__str__()
    
    def copy(self):
        """Create a copy of this time range."""
        return TimeRange(self.start, self.end)

    def duration(self):
        """Get the duration of this time range."""
        if self.is_duration_zero:
            return 0
        elif self.is_duration_inf:
            return np.inf
        else:
            return self.end - self.start
        
    def contains(self, t):
        """Check whether a time value is contained within this time range."""
        return self._start_obj <= t < self._end_obj

    def overlaps(self, other):
        """Check whether this time range overlaps with another time range."""
        if self.is_duration_zero or other.is_duration_zero:
            return False
        else:
            # 補足: 2項目がself.contains(other.end)だと、self.start == other.endのとき、
            # 半開区間同士ゆえに重なっていないのにTrueになってしまう
            return self.contains(other.start) or other.contains(self.start)
    
    def continuous(self, other):
        """Check whether this time range is continuous with another time range."""
        return (self._start_obj == other._end_obj) or (self._end_obj == other._start_obj)

    def intersection(self, other):
        """Get the intersection of this time range with another."""
        new_start_obj = max(self._start_obj, other._start_obj)
        new_end_obj = min(self._end_obj, other._end_obj)
        return TimeRange(new_start_obj, new_end_obj)
    
    def union(self, other):
        """Get the union of this time range with another."""
        if self.overlaps(other) or self.continuous(other):
            # 合計が一つの連続した区間になるとき
            new_start_obj = min(self._start_obj, other._start_obj)
            new_end_obj = max(self._end_obj, other._end_obj)
            return TimeRange(new_start_obj, new_end_obj)
        else:
            # 2つの区間が離れているとき
            return DisjointTimeRanges([self, other])
    
    def to_array(self, unit='D'):
        """
        Returns the time values within the time range as a numpy array.

        The time range is divided into intervals of a specified unit, 
        and each point in time within this range is included in the output array.

        Parameters
        ----------
        unit : str, default 'D'
            Specifies the unit of time to divide the range into. 
            It must comply with numpy.datetime64 units such as 'Y', 'M', 'W', 'D', 
            'h', 'm', 's', 'us', 'ns', 'ps', 'fs', 'as'.

        Returns
        -------
        np.ndarray
            An array containing np.datetime64 values within the time range.

        Raises
        ------
        ValueError
            If the operation is not supported due to infinite time ranges.
        AssertionError
            If the specified unit is not compatible with numpy.datetime64.
        """
        if not (self.start and self.end):
            raise ValueError("Operation not supported for infinite time ranges.")
        
        np_time_units = {'Y','M','W','D','h','m','s','us','ns','ps','fs','as'}
        assert unit in np_time_units

        time_start = self.start.astype(f'datetime64[{unit}]')
        time_stop = self.end.astype(f'datetime64[{unit}]')

        return np.arange(time_start, time_stop, np.timedelta64(1, unit))
    
    def shift(self, dtime):
        """
        Shifts the time range by a certain duration and returns a new TimeRange object.

        Parameters
        ----------
        dtime : np.timedelta64
            The amount of time to shift the range by. It could be positive 
            (shifting into the future) or negative (shifting into the past).

        Returns
        -------
        TimeRange
            A new TimeRange object representing the shifted time range.
        """
        return TimeRange(self.start + dtime, self.end + dtime)
    
    def __bool__(self):
        return not self.is_duration_zero
    
    def __sub__(self, other):
        if isinstance(other, TimeRange):
            if intersection := self.intersection(other):
                ranges = []
                if self._start_obj < intersection._start_obj:
                    ranges.append(TimeRange(self.start, intersection.start))
                if self._end_obj > intersection._end_obj:
                    ranges.append(TimeRange(intersection.end, self.end))
                return DisjointTimeRanges(ranges)
            else:
                return self
        return NotImplemented

    def __or__(self, other):
        if isinstance(other, TimeRange):
            return self.union(other)
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, TimeRange):
            return self.union(other)
        return NotImplemented
    
    def __and__(self, other):
        if isinstance(other, TimeRange):
            return self.intersection(other)
        return NotImplemented
    
    def __xor__(self, other):
        if isinstance(other, TimeRange):
            return (self - other) | (other - self)
        return NotImplemented
    
    def __eq__(self, other):
        if isinstance(other, TimeRange):
            return (self.start == other.start) and (self.end == other.end)
        return NotImplemented
    
class DisjointTimeRanges:
    def __init__(self, ranges=None):
        """
        Initializes the DisjointTimeRanges object to manage a set of disjoint time ranges.
        
        Parameters
        ----------
        ranges : list of TimeRange objects, optional
            A list of TimeRange objects to initialize the DisjointTimeRanges object with.
            Defaults to None, representing all possible intervals.
        
        Attributes
        ----------
        ranges : list of TimeRange objects
            Stores the list of disjoint time ranges managed by this object.
        """
        if ranges is None:
            # rangesの指定がないとき
            # 全区間を表すオブジェクトとする
            self.ranges = [TimeRange()]
        else:
            self.ranges = ranges
        self._consolidate_ranges()
    
    def copy(self):
        """
        Creates a deep copy of the DisjointTimeRanges object.
        
        Returns
        -------
        DisjointTimeRanges
            A new DisjointTimeRanges object that is a copy of the current object.
        """
        return DisjointTimeRanges(ranges=self.ranges)
    
    @staticmethod
    def zero_range():
        """
        Creates a DisjointTimeRanges object representing an empty time range.
        
        Returns
        -------
        DisjointTimeRanges
            A DisjointTimeRanges object representing an empty time range.
        """
        return DisjointTimeRanges(ranges=[])
    
    def _consolidate_ranges(self):
        if len(self.ranges) == 0:
            return
        
        # (start, end)の辞書順でソート
        self.ranges.sort(key=lambda r: (r._start_obj, r._end_obj))
        
        # 重なる範囲をグループ化
        parent_idxs = []
        for i in range(1, len(self.ranges)):
            r0 = self.ranges[i - 1]
            r1 = self.ranges[i]
            if r0.overlaps(r1) or r0.continuous(r1):
                self.ranges[i] |= self.ranges[i - 1]
            else:
                parent_idxs.append(i - 1)
        parent_idxs.append(len(self.ranges) - 1)
                
        # 範囲リストを更新
        self.ranges = [self.ranges[i] for i in parent_idxs if self.ranges[i]]
        self.ranges.sort(key=lambda r: (r._start_obj, r._end_obj))  # 再度ソート
    
    def __repr__(self):
        return f"DisjointTimeRanges({repr(self.ranges)})"
    
    def duration(self):
        """Get the sum of durations of the time ranges."""
        return sum([r.duration() for r in self.ranges])
    
    def contains(self, t):
        """Checks if a specific time is contained within the time ranges."""
        return any(r.contains(t) for r in self.ranges) # any(generator)は短絡評価される
    
    def overlaps(self, other):
        """Checks if two time ranges overlap."""
        if isinstance(other, TimeRange):
            return any(r.overlaps(other) for r in self.ranges)
        elif isinstance(other, DisjointTimeRanges):
            # TODO: ここを効率的に実装する
            return any(self.overlaps(r) for r in other.ranges)
        else:
            raise TypeError(
                f"Expected object of type TimeRange or DisjointTimeRange, but got {type(other).__name__}."
            )
            
    def intersection(self, other):
        """Get the intersection of this time range with another."""
        if isinstance(other, TimeRange):
            return sum([r.intersection(other) for r in self.ranges], TimeRange.zero_range())
        elif isinstance(other, DisjointTimeRanges):
            # TODO: ここを効率的に実装する
            return sum([self.intersection(r) for r in other.ranges], TimeRange.zero_range())
        else:
            raise TypeError(
                f"Expected object of type TimeRange or DisjointTimeRange, but got {type(other).__name__}."
            )
        
    def union(self, other):
        """Get the union of this time range with another."""
        if isinstance(other, TimeRange):
            self._consolidate_ranges()
            new_ranges = DisjointTimeRanges(self.ranges + [other])
            new_ranges._consolidate_ranges()
            return new_ranges
        elif isinstance(other, DisjointTimeRanges):
            self._consolidate_ranges()
            new_ranges = DisjointTimeRanges(self.ranges + other.ranges)
            new_ranges._consolidate_ranges()
            return new_ranges
        else:
            raise TypeError(
                f"Expected object of type TimeRange or DisjointTimeRange, but got {type(other).__name__}."
            )
        
    def to_array(self, unit='D'):
        """
        Returns the time values within the time ranges as a numpy array.

        The time range is divided into intervals of a specified unit, 
        and each point in time within this range is included in the output array.

        Parameters
        ----------
        unit : str, default 'D'
            Specifies the unit of time to divide the range into. 
            It must comply with numpy.datetime64 units such as 'Y', 'M', 'W', 'D', 
            'h', 'm', 's', 'us', 'ns', 'ps', 'fs', 'as'.

        Returns
        -------
        np.ndarray
            An array containing np.datetime64 values within the time range.

        Raises
        ------
        ValueError
            If the operation is not supported due to infinite time ranges.
        AssertionError
            If the specified unit is not compatible with numpy.datetime64.
        """
        self._consolidate_ranges()
        return np.concatenate([r.to_array(unit) for r in self.ranges])
    
    def shift(self, dtime):
        """
        Shifts the time ranges by a certain duration and returns a new DisjointTimeRanges object.

        Parameters
        ----------
        dtime : np.timedelta64
            The amount of time to shift the range by. It could be positive 
            (shifting into the future) or negative (shifting into the past).

        Returns
        -------
        DisjointTimeRanges
            A new DisjointTimeRanges object representing the shifted time ranges.
        """
        new_ranges = [r.shift(dtime) for r in self.ranges]
        return DisjointTimeRanges(new_ranges)
        
    def __bool__(self):
        return len(self.ranges) == 0
    
    def __sub__(self, other):
        if isinstance(other, TimeRange):
            new_ranges = []
            for r in self.ranges:
                substracted = r - other
                if isinstance(substracted, TimeRange):
                    new_ranges.append(substracted)
                elif isinstance(substracted, DisjointTimeRanges):
                    new_ranges += substracted.ranges
            return DisjointTimeRanges(new_ranges)
        elif isinstance(other, DisjointTimeRanges):
            # TODO: ここ効率的に実装する
            new_ranges = sum([(r - other).ranges for r in self.ranges], [])
            return DisjointTimeRanges(new_ranges)
        else:
            return NotImplemented
        
    def __rsub__(self, other):
        if isinstance(other, TimeRange):
            # TODO: ここ効率的に実装する
            new_ranges = other.copy()
            for r in self.ranges:
                new_ranges -= r
            return new_ranges
        else:
            return NotImplemented
        
    def __add__(self, other):
        return self | other
    
    def __radd__(self, other):
        return self | other
        
    def __or__(self, other):
        if isinstance(other, (TimeRange, DisjointTimeRanges)):
            return self.union(other)
        return NotImplemented
    
    def __ror__(self, other):
        return self | other
        
    def __and__(self, other):
        if isinstance(other, (TimeRange, DisjointTimeRanges)):
            return self.intersection(other)
        return NotImplemented
    
    def __rand__(self, other):
        return self & other
    
    def __xor__(self, other):
        if isinstance(other, (TimeRange, DisjointTimeRanges)):
            return (self - other) | (other - self)
        return NotImplemented
        
    def __rxor__(self, other):
        return self ^ other
    
    def __eq__(self, other):
        if isinstance(other, TimeRange):
            return len(self.ranges) == 1 and self.ranges[0] == other
        elif isinstance(other, DisjointTimeRanges):
            # rangeをカノニカルな形式に変換する
            self._consolidate_ranges()
            other._consolidate_ranges()
            
            # rangeの数が一致するかチェック
            if len(self.ranges) != len(other.ranges):
                return False
            
            # rangeがすべて一致するかチェック
            for r1, r2 in zip(self.ranges, other.ranges):
                if r1 != r2:
                    return False
                
            return True
        else:
            return NotImplemented

class TimeSeries(SortedDict):
    """時系列データを保存する辞書。指定時刻に近い時刻のデータをO(log(n))で探す。"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Convert string keys to np.datetime64
        
        # まだ内部ではkeyがstrの場合があるので、__getitem＿内でkeyをstrに変換しない設定にする
        self._is_internal_key_may_str = True 
        items = list(self.items())
        self.clear()
        for key, value in items:
            self[key] = value
        self._is_internal_key_may_str = False
    
    def _key2dt(self, key):
        if isinstance(key, str):
            return np.datetime64(key)
        else:
            return key
        
    def __getitem__(self, key):
        if isinstance(key, slice):
            # key.step は無視する
            start = self._key2dt(key.start)
            stop = self._key2dt(key.stop)
            return TimeSeries({k: self[k] for k in self.irange(start, stop, inclusive=(True, False))})
        else:
            if not self._is_internal_key_may_str:
                # __init__終了後、keyがstrの可能性がなくなったら
                # keyがstrのときは自動的にnp.datetime64に変換する
                key = self._key2dt(key)
            return super().__getitem__(key)
        
    def __setitem__(self, key, value):
        super().__setitem__(self._key2dt(key), value)
    
    def _index_of_last_inclusive(self, key): 
        return self.bisect_right(key) - 1
    
    def _index_of_last_exclusive(self, key):
        return self.bisect_left(key) - 1
    
    def _index_of_next_inclusive(self, key):
        return self.bisect_left(key)
    
    def _index_of_next_exclusive(self, key):
        return self.bisect_right(key)
    
    def last_include_now(self, key):
        """指定時刻以降で最も近い時刻に対応する値を返す"""
        return self._peekitem_only_positive(self._index_of_last_inclusive(key))
    
    def last_exclude_now(self, key):
        """指定時刻より後で最も近い時刻に対応する値を返す"""
        return self._peekitem_only_positive(self._index_of_last_exclusive(key))
            
    def next_include_now(self, key):
        """指定時刻以前で最も近い時刻に対応する値を返す"""
        return self._peekitem_only_positive(self._index_of_next_inclusive(key))
            
    def next_exclude_now(self, key):
        """指定時刻より前で最も近い時刻に対応する値を返す"""
        return self._peekitem_only_positive(self._index_of_next_exclusive(key))
    
    def _peekitem_only_positive(self, i):
        if i < 0: 
            raise IndexError("list index out of range")
        else:
            return self.peekitem(i)
        
# -------trade_time関連----------
        
def previous_day(date):
    return date - datetime.timedelta(days=1)
    
def next_day(date):
    return date + datetime.timedelta(days=1)


def create_trade_time_obj(to_date, TIMEZONE, now):
    class _TradeTime:
        def __init__(self, date=None):
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
                if date >= datetime.date(year=2024, month=11, day=5):
                    # 取引時間延長後のとき
                    self.is_after_arrowhead4 = True
                    self.goba_last = pd.Timestamp(**date_args, hour=15, minute=30)
                    self.five_minutes_before_goba_last = pd.Timestamp(**date_args, hour=15, minute=25) # クロージング・オークション開始
                else:
                    # 取引時間延長前のとき
                    self.is_after_arrowhead4 = False
                    self.goba_last = pd.Timestamp(**date_args, hour=15, minute=00)
                    self.five_minutes_before_goba_last = pd.Timestamp(**date_args, hour=14, minute=55) # 引け5分前(※ザラ場)
                self.is_business_day = TradeTime.is_business_day(date)
                
                self.date = date

        def is_lunch_break(self, time=None, inclusive=False):
            if not self.is_business_day: return False
            time = time or now()
            if inclusive:
                return (self.zenba_last <= time <= self.goba_first)
            else:
                return (self.zenba_last < time < self.goba_first)

        def is_before_start(self, time=None, inclusive=False):
            if not self.is_business_day: return False
            time = time or now()
            if inclusive:
                return (time <= self.zenba_first)
            else:
                return (time < self.zenba_first)

        def is_after_end(self, time=None, inclusive=False):
            if not self.is_business_day: return False
            time = time or now()
            if inclusive:
                return (self.goba_last <= time)
            else:
                return (self.goba_last < time)

        def is_trading_hours(self, time=None, inclusive=True):
            if not self.is_business_day: return False
            time = time or now()
            if inclusive:
                return (self.zenba_first <= time <= self.zenba_last) or (self.goba_first <= time <= self.goba_last)
            else:
                return (self.zenba_first < time < self.zenba_last) or (self.goba_first < time < self.goba_last)

        def is_last_five_minutes(self, time=None, inclusive=True):
            if not self.is_business_day: return False
            time = time or now()
            if inclusive:
                return (self.five_minutes_before_goba_last <= time <= self.goba_last)
            else:
                return (self.five_minutes_before_goba_last < time < self.goba_last)

        def is_closing_auction(self, time=None, inclusive=True):
            if self.is_business_day and self.is_after_arrowhead4:
                return self.is_last_five_minutes(time=time, inclusive=inclusive)
            else:
                return False


    class TradeTime:
        def __init__(self):
            self._date2trade_time_obj = {}
            
        def __getitem__(self, value):
            # デフォルトは現在時刻
            if value is None:
                value = now()
                
            # 指定日の_TradeTimeオブジェクトを未作成なら作る
            date = to_date(value)
            if date not in self._date2trade_time_obj:
                self._date2trade_time_obj[date] = _TradeTime(date)
                
            # 指定日の_TradeTimeオブジェクトを返す
            return self._date2trade_time_obj[date]
        
        def zenba_first(self, date=None):
            return self[date].zenba_first
        
        def zenba_last(self, date=None):
            return self[date].zenba_last
        
        def goba_first(self, date=None):
            return self[date].goba_first
        
        def goba_last(self, date=None):
            return self[date].goba_last
            
        def is_lunch_break(self, time=None, inclusive=False):
            return self[time].is_lunch_break(time, inclusive)
            
        def is_before_start(self, time=None, inclusive=False):
            return self[time].is_before_start(time, inclusive)
        
        def is_after_end(self, time=None, inclusive=False):
            return self[time].is_after_end(time, inclusive)
        
        def is_trading_hours(self, time=None, inclusive=True):
            return self[time].is_trading_hours(time, inclusive)
        
        def is_last_five_minutes(self, time=None, inclusive=True):
            return self[time].is_last_five_minutes(time, inclusive)
        
        def is_closing_auction(self, time=None, inclusive=True):
            return self[time].is_closing_auction(time, inclusive)
            
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

            include_now : bool, default: False
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

            include_now : bool, default: False
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
        
    return TradeTime()
        
    
    
    
    
    
