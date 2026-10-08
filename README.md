# 作业文件整理工具 (Homework Organizer)

一个命令行小工具，帮助你批量整理作业文件。

## 功能

- **扫描与列出**：扫描文件夹，列出文件大小和修改时间，支持按扩展名过滤
- **批量改名**：按规则统一重命名，操作前预览并确认，自动处理重名冲突
- **归档与报告**：按类别移动文件到子文件夹，生成整理报告，支持撤销上次操作

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
python -m homework_organizer list <文件夹>           # 扫描列出文件
python -m homework_organizer rename <文件夹>          # 批量改名
python -m homework_organizer archive <文件夹>         # 归档整理
python -m homework_organizer undo <文件夹>            # 撤销上次操作
```

详见各子命令的 `--help`。
