# Qzone Emoji Crawler

一个可断点续跑的 QQ 空间表情 GIF 爬虫。数据写入 SQLite：

- `Emoji(eid, text, gif)`：成功下载的 GIF。
- `Missing(eid, text)`：服务器明确返回 HTTP 404 的 eid。
- `text` 仅作为兼容旧数据的备注字段保留，默认值为空字符串；爬虫不读取或写入它。
- 超时、网络异常、429 和 5xx 不写入数据库，下次运行会自动重试。

数据库模型和查询使用轻量级 ORM [Peewee](https://docs.peewee-orm.com/) 管理，并兼容已有
`Emoji`、`Missing` 表结构。

## 运行

需要 Python 3.14.x。

安装依赖：

```bash
uv sync
```

扫描默认区间 `0..1001000`：

```bash
uv run python crawl.py
```

指定区间和并发数：

```bash
uv run python crawl.py \
  --start 0 \
  --end 1001001 \
  --concurrency 32 \
  --timeout 15 \
  --db data/emoji.db
```

`--end` 不包含在扫描范围内。已有 GIF 和已经确认 404 的 eid 会自动跳过。

后台运行：

```bash
nohup uv run python crawl.py --concurrency 32 > data/crawl.log 2>&1 &
```

## 代码结构

- `crawl.py`：兼容现有命令的轻量入口。
- `src/config.py`：不可变运行配置与纯函数校验。
- `src/database.py`：Peewee 模型和 SQLite 读写操作。
- `src/downloader.py`：单个 GIF 的下载及结果分类。
- `src/crawler.py`：批处理和断点续跑流程。
- `src/cli.py`：参数解析与命令行启动。

## 开发检查

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
