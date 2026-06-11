# 🐝 PolliPi 实机调试硬件需求清单

> [!NOTE]
> 本报告基于项目源码、README、MASTER_SPEC、DEVICE_ONBOARDING、TROUBLESHOOTING 等全部文档综合整理。

---

## 最小必需设备（单机调试）

| # | 设备 | 型号/规格 | 用途 | 备注 |
|---|------|----------|------|------|
| 1 | **Raspberry Pi** | Pi 5（推荐）/ Pi 4 也可 | 运行 FastAPI 后端、摄像、运动检测、Wi-Fi 热点 | OS: Raspberry Pi OS Bookworm 64-bit |
| 2 | **摄像头模块** | Camera Module 3 Wide (IMX708)（推荐） | 日间延时摄影、运动触发、ROI 录制等 | 见下方详细说明 |
| 3 | **microSD 卡** | 16GB+ | 烧录 OS 和存储数据 | 文档未指定容量，建议 32GB+ |
| 4 | **电源** | USB-C 电源适配器（Pi 5）或充电宝 | 给 Pi 供电 | 需要稳定 5V 输出，注意线材质量 |
| 5 | **客户端设备** | iPad / 任何有浏览器的设备 | PWA 控制界面：设置相机角度、画 ROI、启停录制、查看图像 | 自主录制期间不需要 |
| 6 | **Wi-Fi 网络** | Pi 内置 Wi-Fi 热点 | 客户端与 Pi 通信 | 单机可用 Pi 自带热点 |

---

## 支持的摄像头模块（三选一）

### ✅ Camera Module 3 Wide (IMX708) — 推荐

| 项目 | 详情 |
|------|------|
| **传感器** | `imx708_wide` |
| **最大分辨率** | 4608 × 2592 |
| **类型** | 必需（三种摄像头中选一个） |
| **适用场景** | 日间野外观测主力，延时摄影、运动触发、混合模式、自适应模式、ROI 录制 |
| **配置文件** | `module3_wide_daylight` |
| **环境变量** | `POLLIPI_CAMERA_MODEL=imx708_wide`, `POLLIPI_IS_AI_CAMERA=false`, `POLLIPI_IS_NOIR=false`, `POLLIPI_IS_WIDE=true` |
| **已知部署机** | `zuizui.local`, `zuizui4.local`, `zuizui5.local` |

### 🤖 AI Camera (IMX500) — 可选

| 项目 | 详情 |
|------|------|
| **传感器** | `imx500` |
| **最大分辨率** | 4056 × 3040 |
| **类型** | 可选（用于 AI 推理对比实验） |
| **适用场景** | 传感器端神经网络推理，默认模型为 MobileNet SSD (COCO 标签) |
| **固件安装** | `sudo apt install -y imx500-all && sudo reboot`（**必须在 `install.sh` 之前安装**） |
| **默认模型** | `/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk` |
| **配置文件** | `ai_camera_daylight` |
| **已知部署机** | `zuizui2.local` |

> [!WARNING]
> 默认 COCO 模型**没有 `insect` 标签**——不训练自定义模型则无法识别昆虫！

### 🌙 Camera Module 3 NoIR Wide (IMX708 NoIR) — 可选

| 项目 | 详情 |
|------|------|
| **传感器** | `imx708_noir_wide` |
| **最大分辨率** | 4608 × 2592 |
| **类型** | 可选（低光/夜间实验） |
| **适用场景** | 黄昏/夜间试验，红外照明实验 |
| **配置文件** | `module3_noir_wide_ir` |
| **已知部署机** | `zuizui3.local` |

> [!CAUTION]
> NoIR 摄像头**不能在完全黑暗中自动看到东西**——必须搭配 IR 照明使用！

---

## 可选/扩展设备

| # | 设备 | 用途 | 何时需要 |
|---|------|------|----------|
| 1 | **IR 红外灯** (850nm LED, 低功率) | 给 NoIR 摄像头提供夜间照明 | 仅使用 NoIR 摄像头夜间拍摄时 |
| 2 | **USB SSD / U 盘** | 扩展图像存储空间 | SD 卡容量不够时。配置 `POLLIPI_IMAGE_DIR=/media/your_user/POLLIPI/images` |
| 3 | **UPS HAT** | 电池电量百分比显示 | 想在 App 中查看剩余电量时（⚠️ 代码中**尚未实现**，仅有欠压检测） |
| 4 | **便携 Wi-Fi 路由器** | 多 Pi 组网 | 多台 Pi 同时部署的野外场景 |
| 5 | **显示器 + 键盘** | 初始 Wi-Fi 热点配置 | 仅首次设置时需要（设置热点会断开现有 Wi-Fi） |
| 6 | **外壳/防水壳** | 野外防水防尘 | 户外部署时（文档未提及具体型号） |
| 7 | **三脚架/支架** | 固定相机对准花朵 | 户外部署时（文档未提及具体型号） |

---

## 连线方式

本项目**不使用 GPIO 引脚**，所有连接均为标准接口：

```
┌──────────────┐     CSI 排线      ┌────────────────┐
│  摄像头模块   │ ◄──────────────► │  Raspberry Pi   │
└──────────────┘  (15pin-Pi5     └───────┬────────┘
                   22pin-Pi4)            │
                                    USB-C │ 供电
                                         │
                                   ┌─────▼─────┐
                                   │  电源/充电宝 │
                                   └───────────┘

        Wi-Fi (热点或共享网络)
  ┌──────────┐            ┌────────────────┐
  │  iPad/PC  │ ◄────────► │  Raspberry Pi   │
  └──────────┘            └────────────────┘
```

> [!IMPORTANT]
> **CSI 排线注意**：Pi 5 使用 **15-pin** 排线，Pi 4 使用旧版 **22-pin** 排线，不要搞混！这是 TROUBLESHOOTING.md 中明确提到的常见问题。

---

## 软件依赖（在 Pi 上安装）

| 包名 | 安装方式 | 用途 |
|------|---------|------|
| `python3-picamera2` | `apt install` | 摄像头控制库 |
| `python3-venv` | `apt install` | Python 虚拟环境 |
| `python3-fastapi` | `apt install` | Web API 框架 |
| `python3-uvicorn` | `apt install` | ASGI 服务器 |
| `imx500-all` | `apt install`（仅 AI Camera） | AI 摄像头固件 + 模型 |
| OpenCV (`cv2`) | 运行时依赖 | 图像处理、运动检测、模板匹配、SVM 训练 |
| NumPy | 运行时依赖 | 数组操作 |

---

## 💰 预算估算（仅供参考）

| 设备 | 大致价格 (日元) |
|------|----------------|
| Raspberry Pi 5 (4GB) | ¥9,000 ~ ¥12,000 |
| Camera Module 3 Wide | ¥5,000 ~ ¥6,500 |
| microSD 卡 32GB | ¥800 ~ ¥1,500 |
| USB-C 电源适配器 (5V/3A) | ¥1,500 ~ ¥2,500 |
| **最低总计** | **约 ¥16,300 ~ ¥22,500** |

> [!NOTE]
> 项目文档中**没有提供任何购买链接或零件编号**。价格为市场参考价。

---

## ✅ 快速检查清单

开始调试前，确认你有：

- [ ] Raspberry Pi 5 (或 4) + 电源
- [ ] microSD 卡，已烧录 Raspberry Pi OS Bookworm 64-bit
- [ ] 至少一个支持的摄像头模块 + 正确规格的 CSI 排线
- [ ] 一台有浏览器的设备（iPad/手机/电脑）用于访问 PWA 控制界面
- [ ] 首次设置用的显示器/键盘（或通过有线以太网 SSH）
- [ ] （可选）USB 外部存储、IR 灯、便携路由器等
