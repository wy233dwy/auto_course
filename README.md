# 网课自动化答题工具

自动完成超星学习通和智慧树（知到）的练习题和考试题。

## 功能介绍

- **超星学习通**（学习通）
- **智慧树**（知到）
- 支持 Chrome 和 Edge 浏览器
- 支持所有题型：单选、多选、判断、填空、简答
- 多源联网搜索答案

## 快速开始

```bash
pip install -r requirements.txt
pip install webdriver-manager
python main.py
```

详细使用说明请查看 [README.md](README.md)。

## 项目结构

```
auto_course/
├── main.py                    # 主入口
├── requirements.txt           # 依赖配置
├── core/
│   ├── browser.py             # 浏览器管理（Chrome + Edge）
│   └── answer_searcher.py     # 答案搜索（多源联网）
└── platforms/
    ├── chaoxing.py            # 超星学习通适配器
    └── zhihuishu.py           # 智慧树适配器
```
