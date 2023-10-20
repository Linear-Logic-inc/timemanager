# TimeManager

TimeManagerは、時刻を扱うPythonモジュールです。このモジュールを使用すると、時刻の取得、変換、および管理が容易になります。

<p align="center">
 <img src="https://img.shields.io/badge/python-v3.9+-blue.svg">
 <img src="https://img.shields.io/badge/contributions-welcome-orange.svg">
 <a href="https://opensource.org/licenses/MIT">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg">
 </a>
</p>

## Features

- 現在時刻の取得: 現在の時刻をpandas.Timestamp型で取得します。
- 時刻の変換: UTC時刻や任意のタイムゾーンの時刻をpandas.Timestamp型に変換します。
- プログラムの停止: 指定した秒数や指定した時刻までプログラムを停止します。

## Installation

以下のコマンドを使用して、TimeManagerをインストールしてください。

```
pip install git+https://github.com/FumiYoshida/timemanager
```

## Usage

### Import

基本的な使用方法は以下のとおりです。

```python
import timemanager

# 現在時刻の取得
current_time = timemanager.now()
print(f'Current time: {current_time}')
```

タイムゾーン付きのオブジェクトを使用せずに（単にUTCに+9時間した時刻を扱うことで）高速化したい場合は、以下のようにしてください。

```python
from timemanager import notz as timemanager

# 現在時刻の取得
current_time = timemanager.now()
print(f'Current time: {current_time}')
```
<details>
 <summary><b>Wait Inside Loop</b></summary>

```python
import requests
import timemanager

def scrape_website(url="http://example.com"):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises stored HTTPError, if one occurred.
        print(f"Content from {url}:\n{response.text}\n")
    except requests.exceptions.HTTPError as err:
        print(f"Error: {err}")

while True:
    timemanager.wait_if_pace_too_fast(1)
    scrape_website()
```

このコードは、[example.com](http://example.com)からコンテンツをスクレイピングし、その内容を出力します。`timemanager.wait_if_pace_too_fast(1)`は、スクレイピング関数が1秒に1回以上実行されないように制御します。
</details>
<details>
 <summary><b>`TradeTime` Class</b></summary>

 TradeTimeクラスは、特定の日の取引時間を管理します。インスタンスを初期化する際に、日付を指定することができます。日付を指定しない場合、デフォルトでは現在の日付が使用されます。指定した日付（または現在の日付）に基づいて、取引時間に関する各種の判定が行われます。
 
 <details><summary>現在の日の取引時間に関する情報を取得するコード</summary>
  
 ```python
 from timemanager import trade_time
 
 # 現在が取引時間内であるかどうかを判定
 if trade_time.is_trading_hours():
     print("The market is open now.")
 else:
     print("The market is closed now.")
 ```
 </details>
 <details><summary>指定された日付と時刻について、取引時間内かどうかを確認するコード</summary>
  
 ```python
 from timemanager import TradeTime, from_timezone
 
 # 特定の日付を指定してTradeTimeのインスタンスを作成
 trade_time_specific = TradeTime(date="2023-10-20")
 
 # 特定の日付と時刻が取引時間内であるかどうかを判定
 check_time = from_timezone('2023-10-20T10:00')  # timezone-awareなdatetimeを取得
 
 if trade_time_specific.is_trading_hours(time=check_time):
     print(f"{check_time} is within trading hours.")
 else:
     print(f"{check_time} is outside of trading hours.")
 ```
 
 **Output:**
 ```
 2023-10-20 10:00:00+09:00 is within trading hours.
 ```
 </details>
 <details>
  <summary>Next Business Day</summary>
  
 ```python
 from timemanager import TradeTime
 
 # 指定された日付の翌営業日を取得
 specified_date = '2023-12-29'
 next_day = TradeTime.next_business_day(specified_date)
 
 print(f"The next business day after {specified_date} is {next_day}.")
 ```
 
 **Output:**
 ```
 The next business day after 2023-12-29 is 2024-01-04.
 ```
 
 `TradeTime.next_business_day`メソッドは、指定された日付の次の営業日を返します。銀行カレンダーに基づいているので、土日や銀行休業日が考慮されます。
 </details>
</details>

<details>
<summary><b>`TimeRange` and `DisjointTimeRanges` Classes</b></summary>

### `TimeRange` Class

`TimeRange`は連続した時間範囲[start, end)を扱うクラスです。`numpy.datetime64`がベースで、timezoneには非対応です。

#### 基本的な使い方

```python
from timemanager import TimeRange

# TimeRange インスタンスの作成
time_range = TimeRange('2023-01-01', '2023-01-03')

print(time_range)  # TimeRange('2023-01-01', '2023-01-03')
print(time_range.duration())  # 2 days

# 時刻が範囲内にあるか確認
print(time_range.contains('2023-01-02'))  # True

# 他のTimeRangeとの重複確認
other_range = TimeRange('2023-01-02', '2023-01-04')
print(time_range.overlaps(other_range))  # True

# 他のTimeRangeとの共通範囲
intersection_range = time_range.intersection(other_range)
print(intersection_range)  # TimeRange('2023-01-02', '2023-01-03')

# 他のTimeRangeとの合成
union_range = time_range.union(other_range)
print(union_range)  # TimeRange('2023-01-01', '2023-01-04')
```

### `DisjointTimeRanges` Class

`DisjointTimeRanges`は連続した時間範囲の集合を扱うクラスです。`numpy.datetime64`がベースで、timezoneには非対応です。

#### 基本的な使い方

```python
from timemanager import DisjointTimeRanges, TimeRange

# DisjointTimeRanges インスタンスの作成
disjoint_ranges = DisjointTimeRanges()

# 時間範囲の追加
disjoint_ranges.add_range('2023-01-01', '2023-01-03')
disjoint_ranges.add_range('2023-01-05', '2023-01-07')

print(disjoint_ranges)  # DisjointTimeRanges([TimeRange('2023-01-01', '2023-01-03'), TimeRange('2023-01-05', '2023-01-07')])

# TimeRangeの追加
new_range = TimeRange('2023-01-02', '2023-01-04')
updated_ranges = disjoint_ranges + new_range
print(updated_ranges)  # DisjointTimeRanges([TimeRange('2023-01-01', '2023-01-04'), TimeRange('2023-01-05', '2023-01-07')])

# TimeRangeの削除
remove_range = TimeRange('2023-01-02', '2023-01-03')
updated_ranges = disjoint_ranges - remove_range
print(updated_ranges)  # DisjointTimeRanges([TimeRange('2023-01-01', '2023-01-02'), TimeRange('2023-01-05', '2023-01-07')])
```
</details>

上記は、`TimeRange`と`DisjointTimeRanges`クラスの基本的な使い方を示す例です。これらのクラスは、特定の時間範囲や、その集合を簡単に管理するために使用できます。

## Contributing

バグレポートやフィーチャーリクエストは、GitHubのissueでお知らせください。また、プルリクエストも大歓迎です。

## License

このプロジェクトはMITライセンスのもとで公開されています。詳細は[LICENSE](https://github.com/FumiYoshida/timemanager/blob/main/LICENSE)をご覧ください。

以下は、TimeManagerモジュールの基本的な機能をテストするPythonコードです。

```python
import timemanager
import pandas as pd

# 現在時刻の取得
current_time = timemanager.now()
assert isinstance(current_time, pd.Timestamp), 'Error: Current time should be a pandas.Timestamp.'

# 時刻の変換
converted_time = timemanager.from_utc('2022-01-01T00:00:00Z')
assert isinstance(converted_time, pd.Timestamp), 'Error: Converted time should be a pandas.Timestamp.'
assert converted_time == pd.Timestamp('2022-01-01T09:00:00', tz='Asia/Tokyo'), 'Error: Converted time is incorrect.'

# プログラムの停止
start_time = pd.Timestamp.now()
timemanager.wait(2)
end_time = pd.Timestamp.now()
assert (end_time - start_time).total_seconds() >= 2, 'Error: Wait function did not pause execution for at least 2 seconds.'
```
