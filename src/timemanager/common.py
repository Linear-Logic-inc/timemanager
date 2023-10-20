import numpy as np
from sortedcontainers import SortedDict

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