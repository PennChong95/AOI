# AOI 复判系统 V4.1

基于 PyQt5 的桌面端 AOI 检测结果复判与质量分析系统，集成指纹登录、示意图编辑器、质量看板等功能模块。

---

## 功能概览

### 复判主界面
- 产品 SN 查询检索
- 检测图像查看（支持缩放、平移、缺陷框叠加）
- 九宫格辅助定位
- 检测结果复判（OK / NG）
- 历史记录查询
- 指纹 / 密码双模登录与会话超时重认证

### 质量分析看板
- KPI 指标面板（总投入、OK数、NG数、良率、复判后良率等，支持自定义显示项）
- 良率趋势折线图（支持多粒度：10分钟/小时/天/周/月）
- 缺陷分布环形图 / 柱状图
- 缺陷 Pareto 分析（80/20 法则）
- 产品缺陷区域热力图（产品示意图 / 色块占比双视图）
- 最近检测记录表格
- 图片查看器（联动数据钻取，点击缺陷/区域自动筛选图片）
- 可拖拽卡片工作区，支持 6 种布局预设
- 布局持久化保存与恢复

### 示意图编辑器
- 可视化编辑产品区域布局
- 矩形 / 圆形区域标注
- 区域颜色、层级、可见性管理
- 布局保存与热力图联动

### 系统设置
- 数据库连接管理（多数据库、启用/禁用、测试连接）
- 缺陷显示参数（框倍率、线宽、颜色）
- 九宫格网格线样式
- 用户管理与指纹注册
- 登录模式切换（指纹/密码）
- 复判判定约束配置
- 复判模式选择（图像优先 / 区域优先）

---

## 技术栈

| 组件 | 技术 |
|---|---|
| 语言 | Python 3.12+ |
| GUI 框架 | PyQt5 |
| 数据库 | MySQL（支持分表路由：热表 + 历史月表） |
| 图表 | matplotlib + ECharts（降级使用） |
| 指纹识别 | ZKFinger SDK（USB 指纹仪） |
| 打包 | PyInstaller + Inno Setup |

---

## 项目结构

```
AOI_Reviewer_V4.1/
├── main.py                     # 入口文件
├── auth/                       # 指纹/密码登录
├── review/                     # 复判主界面
│   ├── main_window.py          # 主窗口（1762 行）
│   ├── thumbnail_panel.py      # 缩略图面板
│   └── product_view_widget.py  # 产品示意图控件
├── dashboard/                  # 质量看板
│   ├── window.py               # 看板主窗口
│   ├── core/                   # 卡片工作区、拖拽布局、事件总线
│   ├── cards/                  # 图片查看器、热力图卡片
│   ├── pages/                  # 看板页面
│   └── dialogs/                # 设置、导出弹窗
├── editor/                     # 示意图编辑器
├── analytics/                  # 数据分析层（良率、缺陷、热力等）
├── services/                   # 业务服务层
├── database/                   # 数据库管理器、分表路由
├── ui/                         # UI 组件、图表、KPI 卡片
├── utils/                      # 配置管理、导出工具
├── modes/                      # 复判模式
├── libzkfpcsharp.dll           # 指纹 SDK
└── build_installer.bat         # 一键打包脚本
```

---

## 快速开始

### 环境要求

- Python 3.12 或 3.13
- MySQL 数据库
- （可选）ZKFinger 兼容的 USB 指纹仪

### 安装

```bash
cd AOI_Reviewer_V4.1
pip install -r requirements.txt
python main.py
```

### 首次使用

1. 启动后自动读取 `%APPDATA%/InspectionReview/config.json` 中的数据库配置
2. 如无配置文件，会提示数据库连接失败，可在设置页面中配置
3. 配置好数据库后重启，进入登录界面
4. 默认账号：`admin` / `admin123`

---

## 打包

### 生成可执行文件

```bash
# 一键打包（PyInstaller + Inno Setup）
双击 build_installer.bat
```

### 输出目录

```
dist/main/          ← PyInstaller 打包产物
  └── main.exe      ← 主程序
  └── _internal/    ← 运行时库
installer_output/   ← Inno Setup 安装包
```

---

## 数据库说明

详见 [表结构文档](./表结构文档.md)

### 分表策略
- `_current` 后缀：最近 30 天热数据
- `_history_YYYYMM` 后缀：按月归档的冷数据
- 由 `TableRouter` 自动路由

---

## 配置

配置文件位于 Windows 的 `%APPDATA%/InspectionReview/` 目录：

| 文件 | 说明 |
|---|---|
| `config.json` | 数据库配置、显示参数、登录模式等 |
| `users.json` | 用户账号与指纹模板 |

---

## 许可证

仅供内部使用
