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

### Wait inside loop
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

このコードは、指定したURL（この場合は [example.com]("http://example.com")）からコンテンツをスクレイピングし、その内容を出力します。`timemanager.wait_if_pace_too_fast(1)`は、スクレイピング関数が1秒に1回以上実行されないように制御します。


詳細なドキュメンテーションは、[こちら](https://github.com/FumiYoshida/timemanager/wiki)をご覧ください。

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
