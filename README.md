# DMM6500 综合监控台

> 一款基于 **PyQt6 + PyVISA** 的 Keithley / Tektronix **DMM6500** 数字万用表上位机监控软件。

<p align="center">
  <img src="DMM6500_app.ico" width="96" alt="DMM6500 Monitor">
</p>

<p align="center">
  <b>实时波形 · 统计 · 报警 · HTML 报告 · 授权系统 · 5 套主题</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/PyQt6-6.x-green" alt="PyQt6">
  <img src="https://img.shields.io/badge/pyvisa-latest-orange" alt="pyvisa">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License">
</p>

---

作者：**得鹿梦鱼** &nbsp;·&nbsp; 「莫道桑榆晚，为霞尚满天」

---

## 📖 目录

- [✨ 特性](#-特性)
- [📦 系统要求](#-系统要求)
- [🚀 安装](#-安装)
- [🎯 快速开始](#-快速开始)
- [🖱️ 鼠标 / 键盘操作](#️-鼠标--键盘操作)
- [📊 支持的测量模式](#-支持的测量模式)
- [📂 目录结构](#-目录结构)
- [🔐 授权系统](#-授权系统)
- [📝 命令行参数](#-命令行参数)
- [🛠️ 打包发布](#️-打包发布)
- [📄 许可](#-许可)

---

## ✨ 特性

- **实时波形** &mdash; 高刷新率绘制，自动降采样，10 万+ 数据点无卡顿
- **多阈值报警** &mdash; 同一曲线可挂多条独立规则，各自去重
- **数据记录** &mdash; CSV 自动分卷，每 10 万行切分
- **HTML 报告** &mdash; 单文件交互式报告，内嵌 ECharts 波形，可离线查看
- **缓存下载** &mdash; 从仪器内部缓冲区下载历史数据
- **十字线浮动标签** &mdash; 60ms 节流 + 边界/曲线/游标完整避让
- **游标测量** &mdash; 双游标拖动，实时显示 ΔX / ΔY
- **5 套主题** &mdash; light / dark / nord / solarized_light / dracula，`Ctrl+T` 循环切换
- **授权系统** &mdash; RSA 签名 + 硬件指纹 + 试用期 + 多应用隔离

---

## 📦 系统要求

| 项目 | 要求 |
|------|------|
| Python | 3.9 及以上 |
| 操作系统 | Windows / macOS / Linux |
| 仪器 | Keithley / Tektronix DMM6500（以太网 / USB） |

**依赖库**：

```bash
PyQt6
pyqtgraph
pyvisa
pyvisa-py      # 可选，纯 Python VISA 后端
numpy
cryptography
Pillow         # 可选，应用图标生成
```

---

## 🚀 安装

### 方式一：从源码运行

```bash
git clone https://github.com/lxxvah/dmm6500.git
cd dmm6500

pip install PyQt6 pyqtgraph pyvisa numpy cryptography Pillow
```

### 方式二：使用打包好的安装包

下载 `DMM6500_Setup_v1.0.0.exe` → 双击安装 → 开始菜单/桌面会出现快捷方式。

---

## 🎯 快速开始

```bash
python main.py
```

首次启动流程：

1. **授权对话框**弹出 → 选择「1 天试用」或粘贴授权密钥
2. 进入主界面 → 左侧面板填 **IP 或 VISA 地址** → 点「扫描」或「连接」
3. 选择测量功能（DCV / DCI / RES2W / RES4W / …）
4. 数据开始实时采集 → 波形、统计、报警同步工作

---

## 🖱️ 鼠标 / 键盘操作

### 波形区

| 操作 | 说明 |
|------|------|
| **滚轮** | 缩放 X 轴（时间轴） |
| **Ctrl + 滚轮** | 缩放 Y 轴（读数轴） |
| **左键拖动** | 平移视图 |
| **中键拖动** | 沿单轴缩放 |
| **右键拖动** | 矩形框缩放 |
| **右键单击** | 弹出菜单（显示全部 / 功能介绍 / 9 项开关） |
| **拖动游标** | 移动两根垂直游标线，标签自动避让 |
| **十字线跟随** | 鼠标在绘图区内时自动显示交点标签 |

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + T` | 循环切换 5 个主题 |

---

## 📊 支持的测量模式

| 分类 | 模式 | 说明 |
|------|------|------|
| **DC 直流** | `DCV` | 直流电压 |
| | `DCI` | 直流电流 |
| | `RES2W` | 2 线电阻 |
| | `RES4W` | 4 线电阻 |
| **AC 交流** | `ACV` | 交流电压 |
| | `ACI` | 交流电流 |
| | `CAP` | 电容 |
| **频率 / 周期** | `FREQ` | 频率 |
| | `PER` | 周期 |
| **其他** | `TEMP` | 温度（默认 K 型热电偶） |
| | `CONT` | 通断 |
| | `DIOD` | 二极管 |

---

## 📂 目录结构

```
dmm6500/
├── main.py                     # 程序入口
├── theme.py                    # 多主题配色
├── DMM6500_Setup.iss           # Inno Setup 安装脚本
├── DMM6500_app.ico             # 应用图标
├── build_DMM6500.bat           # 一键打包脚本
│
├── core/                       # 核心逻辑
│   ├── connection.py           # 连接 / 扫描管理
│   ├── measurements.py         # 12 种测量功能
│   ├── statistics.py           # 流式统计 & 单位自适应
│   ├── recorder.py             # CSV 记录
│   ├── alarm.py                # 报警管理
│   ├── report.py               # HTML 报告生成
│   └── buffer_downloader.py    # 仪器缓存下载
│
├── ui/                         # 界面组件
│   ├── monitor_window.py       # 主窗口
│   ├── control_panel.py        # 左侧控制面板
│   ├── waveform_widget.py      # 波形控件
│   ├── cards.py                # 卡片 & 对话框
│   └── about_dialog.py         # 功能介绍对话框
│
├── licensing/                  # 授权模块（客户端）
│   ├── config.py               # 唯一要改的配置文件
│   ├── client.py               # 授权校验核心
│   ├── fingerprint.py          # 硬件指纹采集
│   ├── dialog.py               # 授权对话框
│   ├── request_dialog.py       # 授权申请对话框
│   ├── license_gate.py         # 一行式授权闸门
│   └── public_key.pem          # RSA 公钥
│
├── libs/                       # 工具库
│   ├── DMM6500.py              # 仪器 SCPI 封装
│   ├── DMM6500app_icon.py      # 主题图标生成
│   ├── platform_utils.py       # 平台工具
│   └── loading.py              # 终端 loading 指示器
│
├── tools/                      # 作者端签发工具
│   ├── keygen_gui.py           # 授权签发工具（GUI）
│   ├── generate_keys.py        # RSA 密钥对生成
│   ├── apps_config.py          # 多应用配置
│   └── integrate_licensing.py  # 一键集成到其他工程
│
└── tests/                      # 单元测试
```

---

## 🔐 授权系统

本项目内置完整的授权系统，支持：

- **RSA-2048 签名** &mdash; 抗篡改，防伪造
- **硬件指纹绑定** &mdash; 一机一码
- **多应用隔离** &mdash; 一个工具可给多个软件签发
- **试用期管理** &mdash; 多位置冗余存储，防时间回退
- **离线激活** &mdash; 无需服务器

### 客户端集成到新工程

只需 3 步：

```bash
# 1. 拷贝 licensing/ 文件夹和公钥
cp -r dmm6500/licensing  your_project/licensing
cp dmm6500/tools/public_key.pem  your_project/licensing/

# 2. 修改 licensing/config.py 里 4 个变量
APP_ID       = "your_app_id"
APP_NAME     = "你的应用名"
KEY_PREFIX   = "YOURAPP-"
AUTHOR_EMAIL = "your@email.com"

# 3. 主程序加 3 行
from licensing import ensure_licensed
if not ensure_licensed():
    sys.exit(0)
```

### 更多文档

- 授权签发：`tools/keygen_gui.py`
- 自动集成：`python tools/integrate_licensing.py`

---

## 📝 命令行参数

```bash
python main.py --dark                # 深色主题启动
python main.py --theme dracula       # 指定主题启动
python main.py --show-license        # 打印本机机器码后退出
```

**可用主题**：`light` / `dark` / `nord` / `solarized_light` / `dracula`

---

## 🛠️ 打包发布

### 打包成 exe（PyInstaller）

双击 `build_DMM6500.bat`，或命令行：

```bash
pyinstaller --windowed --name DMM6500 \
    --icon DMM6500_app.ico \
    --add-data "licensing/public_key.pem;licensing" \
    --hidden-import cryptography \
    --hidden-import pyvisa \
    --hidden-import pyvisa_py \
    --hidden-import pyqtgraph \
    --noconfirm main.py
```

输出：`dist/DMM6500/DMM6500.exe`

### 制作安装包（Inno Setup）

1. 安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)
2. 双击 `DMM6500_Setup.iss`
3. 按 `F9` 编译
4. 输出：`Output/DMM6500_Setup_v1.0.0.exe`

---

## 📄 许可

本项目采用 **MIT License**，详见 [LICENSE](LICENSE)。

---

## 🙏 致谢

- [pyqtgraph](https://github.com/pyqtgraph/pyqtgraph) &mdash; 高性能科学绘图
- [PyVISA](https://pyvisa.readthedocs.io/) &mdash; VISA 仪器控制
- [ECharts](https://echarts.apache.org/) &mdash; 交互式图表

---

<p align="center">
  <i>「莫道桑榆晚，为霞尚满天」</i><br>
  <sub>Made with ❤️ by 得鹿梦鱼</sub>
</p>