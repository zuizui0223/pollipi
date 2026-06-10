# PolliPi Monorepo Migration Plan

## 目标

把当前根目录里的单文件后端和 `web/` 下的 DOM 脚本，迁移到已有的 monorepo 结构中：

- `pollipi_api_server.py` 只作为迁移来源，正式源码落到 `packages/server`。
- `web/app.js` 只作为迁移来源，正式前端落到 `packages/web`，用 Preact + Signals 重构。
- `packages/server` 现有占位端点直接移除，新的 API surface 由迁移后的 PolliPi 功能重新建立。
- 后端提供 Raspberry Pi 环境启动和数据交换验证的 CI/CD。
- 后端提供构建单个 Python 脚本的产物，方便继续按现有 Pi 部署方式分发。
- 不处理 `legacy/`。

## 当前状态

- 根目录 `pollipi_api_server.py` 约 2600 行，混合了配置、Pydantic schema、FastAPI app、硬件调用、timelapse 控制、CSV 事件存储、图片管理、训练逻辑、ROI 建议、MJPEG/preview、静态 `web/` 挂载。
- `packages/server` 已存在 Python 包骨架，但当前只有 `GET /health` 和 `GET /api/v1/runtime/status` 两个占位端点。
- `web/app.js` 约 1500 行，使用直接 DOM 查询和全局可变状态管理多设备、ROI、gallery、event review、training。
- `packages/web` 已有 Vite + Preact + `@preact/signals` + vanilla-extract scaffold。
- `packages/contracts` 已有少量 TS 类型，但还不能覆盖现有 PolliPi API。
- 部署脚本和文档仍以根目录 `pollipi_api_server.py`、`web/`、`uvicorn pollipi_api_server:app` 为中心。
- GitHub Actions 目前只有通用 Python syntax check 和模板 PyPI publish workflow。

## 2026-06-10 审计状态

已完成或已补齐：

- `packages/server/src/visit_monitor_server` 已拆出 app factory、config、API router、schema、routes、services、adapters，原占位端点不再挂到新 app。
- 旧 API surface 的主要路径已在新 router 中恢复：`/start`、`/stop`、`/status`、`/device`、`/system`、`/latest`、`/preview`、`/mjpeg`、`/roi/suggest`、`/images`、`/exports/images.zip`、`/events`、`/training/*`。
- 已新增 fake-camera HTTP smoke test，覆盖 `/device`、`/status`、`/start`、`/images`、`/latest`、`/training/status`、`/stop`。
- 已新增 `visit_monitor_server.distribution.bundle_single_file`，可生成 `dist/pollipi_api_server.py`，产物暴露 `app` 并支持直接运行。
- `.github/workflows/server-ci.yml` 已覆盖 Python compile、pytest fake-camera smoke、单文件构建、单文件 compile、单文件 fake-camera smoke、artifact 上传、Pi self-hosted smoke。
- `packages/web` 的 Preact 组件/state/API client 已接到 `app.tsx`，不再停留在 scaffold 首屏；gallery、event review、training 的异步加载已改为 effect 驱动。
- `pnpm check:web`、`pnpm build:web`、`pytest packages/server`、单文件 bundle smoke 在本地通过。

仍未完成：

- 根目录 `pollipi_api_server.py` 仍是旧手写迁移来源，尚未替换为构建产物或兼容 shim。
- 根目录 `web/` 仍是旧前端来源，尚未删除、归档或改为 `packages/web/dist` 的发布产物。
- `install.sh`、`setup_device.sh`、`deploy_pollipi_pi.ps1`、`README.md`、`QUICKSTART.md`、`DEVICE_ONBOARDING.md` 尚未全面切换到 artifact/install flow。
- CI/CD 的 CD job 仍主要发布后端单文件，尚未同时构建并上传 web build。
- Raspberry Pi 真实 Picamera2/IMX500 路径仍需要 self-hosted Pi runner 或实机验证。

## 迁移原则

- 先保留行为，再换结构。旧单文件作为对照物，迁移后用 smoke/API 测试确认关键路径。
- `packages/server` 是后端唯一源码真相；根目录单文件以后由构建脚本生成，不再手工维护。
- `packages/web` 是前端唯一源码真相；根目录 `web/` 在迁移完成后删除或改为构建产物来源。
- API 字段名要先冻结，避免 Python snake_case 和 TS camelCase 在重构中漂移。
- 硬件相关代码必须隔离到 adapter/service 层，让 CI 可以用 fake camera 跑完启动和数据交换。
- Raspberry Pi 专属验证使用 self-hosted Pi runner；普通 PR 仍能在 GitHub-hosted Ubuntu 上跑纯软件测试。

## 后端目标结构

建议把 `packages/server/src/visit_monitor_server` 收敛为：

```text
visit_monitor_server/
  __init__.py
  main.py
  config.py
  app.py
  api/
    __init__.py
    router.py
    schemas/
      capture.py
      device.py
      events.py
      images.py
      roi.py
      training.py
    routes/
      capture.py
      device.py
      events.py
      images.py
      preview.py
      roi.py
      training.py
  services/
    controller.py
    capture_loop.py
    event_log.py
    image_store.py
    motion.py
    roi_tracking.py
    training.py
  adapters/
    camera.py
    fake_camera.py
    imx500.py
    system_info.py
  distribution/
    bundle_single_file.py
```

迁移映射：

- `StartRequest`、`StatusResponse`、图片/事件/训练/ROI schema 拆到 `api/schemas/*`。
- `TimelapseController` 拆到 `services/controller.py`，把循环、状态快照、持久化 autonomous config 分离。
- 图片目录、CSV、ZIP、删除、label 操作放到 `services/image_store.py` 和 `services/event_log.py`。
- motion diff、ROI clamp/tracking、ROI suggestion 放到 `services/motion.py` 和 `services/roi_tracking.py`。
- Picamera2、IMX500、OpenCV、subprocess/system probes 放到 `adapters/*`。
- FastAPI app factory 放到 `app.py`，`main.py` 只暴露 `app = create_app()` 和 CLI 入口。
- 删除当前 `packages/server/src/visit_monitor_server/api/routes.py` 的占位端点，改为聚合新 routers。

## API 合约

第一阶段不要顺手重命名外部字段。优先迁移现有前端依赖的路径和响应：

- capture/control: `/start`, `/stop`, `/status`
- device/system: `/device`, `/system`
- media stream: `/latest`, `/preview`, `/mjpeg`
- ROI: `/roi/suggest`
- images: `/images`, `/images/{filename}`, `/exports/images.zip`, image label/delete
- events: `/events`, `/events/{event_id}/label`, `/events/export_labels.csv`
- training: `/training/status`, `/training/start`, `/training/model`

之后再决定是否加 `/api/v1` 命名空间。若要加版本化路径，先在 contracts 里声明映射，再让前端通过 API client 切换，避免半迁移状态。

## 前端目标结构

建议把 `packages/web/src` 拆为：

```text
src/
  app.tsx
  api/
    client.ts
    types.ts
  state/
    devices.ts
    session.ts
    gallery.ts
    events.ts
    training.ts
  components/
    DeviceForm.tsx
    DeviceGrid.tsx
    DeviceCard.tsx
    FieldControls.tsx
    RoiEditor.tsx
    Gallery.tsx
    EventReview.tsx
    TrainingPanel.tsx
  lib/
    roi.ts
    formatting.ts
    storage.ts
```

迁移方式：

- 从 `web/app.js` 提取纯函数：base URL 解析、ROI normalize/clamp、时间/容量格式化、payload 组装。
- 用 `signal`/`computed` 管理设备列表、选中 gallery camera、collection tab、event category、session metadata、busy/offline 状态。
- 用组件替代 DOM template：设备卡、ROI 编辑器、gallery item、event review item、training panel。
- API 请求集中到 `api/client.ts`，所有 endpoint 路径和 request/response 类型从 contracts 或本地类型导入。
- `localStorage` 读写集中到 `state/devices.ts` 或 `lib/storage.ts`，保留 `pollipi.observationDevices.v2` 兼容读取。
- ROI 拖拽逻辑先搬成可测试的纯几何函数，再接入 Preact pointer handlers。
- 样式继续用 vanilla-extract，但迁移时先忠实恢复现有工作流，不做大视觉改版。

## 单文件后端产物

后端源码模块化后，新增构建命令生成单个脚本：

```bash
python -m visit_monitor_server.distribution.bundle_single_file \
  --output dist/pollipi_api_server.py
```

产物要求：

- `dist/pollipi_api_server.py` 内联本仓库的 `visit_monitor_server` 模块。
- 第三方依赖仍使用 Pi 系统或 venv 中的 `fastapi`、`uvicorn`、`picamera2`、`cv2` 等，不塞进脚本。
- 产物暴露 `app`，兼容 `python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000`。
- 产物也支持直接运行：`python pollipi_api_server.py --host 0.0.0.0 --port 8000`。
- CI 每次构建后对产物执行 `py_compile` 和一次 fake-camera smoke test。

实现可选方案：

- 优先使用一个仓库内构建脚本，基于 Python AST/模块图读取本地包并生成单文件。
- 若自研成本过高，使用 `stickytape` 之类的 dev dependency，但要把版本固定在 server 构建依赖里。

## Raspberry Pi CI/CD

新增 workflow：`.github/workflows/server-ci.yml`。

普通 CI job：

- 安装 `packages/server`。
- 运行 Python compile/type/test。
- 用 fake camera 启动 ASGI app。
- 通过 HTTP client 验证启动和数据交换：device/status/start/stop/images/events/training 的最小闭环。
- 构建 `dist/pollipi_api_server.py` 并上传 artifact。

Raspberry Pi validation job：

- 使用 self-hosted runner labels，例如 `self-hosted`, `linux`, `arm64`, `raspberry-pi`。
- 安装或复用 Pi 上的系统依赖：`python3-picamera2`, `python3-fastapi`, `python3-uvicorn`。
- 下载 CI 生成的单文件脚本或从当前 checkout 构建。
- 设置临时 `POLLIPI_IMAGE_DIR`，以 fake camera 或可选真实 Picamera2 adapter 启动服务。
- 启动 `uvicorn pollipi_api_server:app`，等待端口可用。
- 执行 exchange smoke：
  - `GET /device`
  - `GET /status`
  - `POST /start`
  - 等待至少一次 fake capture 或硬件 capture
  - `GET /latest` 或 `GET /images`
  - `POST /stop`
- 收集 server log、生成图片、CSV 作为 artifact。

CD job：

- `main` 分支构建并上传 `pollipi_api_server.py`、web build、install/setup 脚本。
- `workflow_dispatch` 支持部署到指定测试 Pi。
- 部署后复用同一套 exchange smoke，失败则不标记发布成功。

## 部署脚本和文档迁移

后端和前端迁移完成后再更新：

- `install.sh`：安装包依赖，并保留 system-site-packages 用于 Picamera2。
- `setup_device.sh`：systemd `ExecStart` 指向新包入口或单文件产物。
- `deploy_pollipi_pi.ps1`：上传 `dist/pollipi_api_server.py` 和 `packages/web/dist`，不再上传根目录源码文件。
- `README.md`、`QUICKSTART.md`、`DEVICE_ONBOARDING.md`：把 `pollipi_api_server.py` 的手工复制说明改成 artifact/install flow。

## 实施顺序

1. 建立后端测试壳：fake camera、临时图片目录、HTTP smoke fixture。
2. 删除 `packages/server` 占位 router，把 app factory 改成聚合 router 入口。
3. 逐块迁移 schema、config、image/event store，不接硬件。
4. 迁移 controller 和 capture loop，硬件调用全部经 adapter。
5. 接回现有 API 路径，跑旧前端依赖的 smoke test。
6. 新增单文件构建命令，验证生成脚本可启动。
7. 新增 GitHub Actions 普通 CI 和 Raspberry Pi self-hosted validation。
8. 提取 TS API types/contracts，迁移 `web/app.js` 的纯函数。
9. 用 Preact + Signals 重建设备控制、ROI、gallery、events、training。
10. 切换部署脚本和文档，删除或归档根目录 `web/` 与手写单文件来源。

## 验收标准

- `pollipi_api_server.py` 不再是手写源码入口；后端源码在 `packages/server`。
- `packages/server` 没有迁移前的占位端点。
- `packages/web` 可以完成现有 PWA 的主要现场工作流。
- `pnpm build:web` 通过。
- `packages/server` 的 fake-camera smoke test 通过。
- CI 上传单文件后端 artifact。
- Raspberry Pi self-hosted validation 能启动服务并完成 HTTP 数据交换。
- 部署脚本可以把单文件后端和 web build 推到 Pi，并通过部署后 smoke。

## 主要风险

- Picamera2/OpenCV/IMX500 只能在 Pi 上完整验证，必须用 adapter + fake camera 保证非 Pi 环境可测。
- CSV schema 目前承担事件数据兼容职责，迁移时不能随意丢列或改列名。
- 前端 ROI 拖拽和多设备状态耦合很重，迁移时应先迁纯函数再迁 UI。
- 单文件构建不能隐藏真实第三方依赖，Pi 安装脚本仍要清楚安装系统包。
- API 版本化最好等行为迁移稳定后再做，避免同时迁结构、路径、字段三件事。
