# 保研 DDL 雷达

一个面向计算机保研夏令营、预推免、九推信息的静态收集网站。第一版不需要数据库和后端，直接部署到 GitHub Pages、Cloudflare Pages、Vercel 或任意静态服务器。

`data/schools.json` 采用“官网采集友好”的目标口径：985、211、中国科学院大学，以及部分 211 异地校区或独立官网入口会单独列出，便于后续按入口抓取通知。

## 怎么更新数据

1. 打开网站底部的“新增记录生成器”。
2. 填入学校、学院、类型、截止时间、官方链接等字段。
3. 复制生成的 JSON。
4. 追加到 `data/notices.json` 数组中。
5. 运行校验脚本：

```bash
python scripts/validate_data.py
```

每条通知都建议保留官方来源链接，并把 `verified` 设为 `true` 只表示“人工核验过来源和截止时间”，不代表替代学校官网。

## 数据字段

```json
{
  "id": "zju-cs-2026-pretui",
  "school": "浙江大学",
  "college": "计算机科学与技术学院",
  "type": "预推免",
  "title": "官方通知标题",
  "deadline": "2026-09-12T17:00:00+08:00",
  "sourceUrl": "https://...",
  "applyUrl": "https://...",
  "tags": ["985", "211", "计算机", "预推免"],
  "lastCheckedAt": "2026-08-05",
  "verified": true
}
```

## 部署方式

### GitHub Pages

1. 新建 GitHub 仓库并上传这些文件。
2. 在仓库设置中打开 Pages。
3. Source 选择 `Deploy from a branch`。
4. Branch 选择 `main`，目录选择 `/root`。

### Cloudflare Pages

1. 连接 GitHub 仓库。
2. Framework preset 选择 `None`。
3. Build command 留空。
4. Output directory 填 `/`。

### Vercel

1. 导入 GitHub 仓库。
2. Framework preset 选择 `Other`。
3. Build command 留空。
4. Output directory 填 `.`。

## 每日自动抓取与审核

现在已经包含每日抓取流程：GitHub Actions 每天北京时间 09:15 执行
`scripts/crawl_sources.py`，逐一检索 `data/schools.json` 中的 118 个目标，
只接受 `.edu.cn` 和 `.ac.cn` 官方页面。新发现只写入
`data/pending-notices.json`，不会直接出现在公开列表。

查看待审核记录：

```bash
python scripts/review_pending.py --list
```

审核通过；如果脚本未识别截止时间，需要用 `--deadline` 补齐：

```bash
python scripts/review_pending.py --approve auto-记录ID \
  --deadline 2026-09-12T17:00:00+08:00 \
  --college 计算机学院
```

驳回误报：

```bash
python scripts/review_pending.py --reject auto-记录ID
```

`data/source-overrides.json` 存放优先直抓入口。某所学校官网检索效果不佳时，
把其研究生院或计算机学院招生通知列表页加到这里即可；抓取器仍会进行官网域名、
学校名和推免关键词校验。

## 本地预览

Windows PowerShell：

```powershell
.\scripts\serve.ps1
```

然后打开：

```text
http://127.0.0.1:8000/
```
