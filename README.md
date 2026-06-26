# Bambu 打印状态 & Access Token 获取

[English](./README.en.md) · 简体中文

一个网页应用，用于查看拓竹（Bambu Lab）打印机的实时状态，并获取中国区账号的 Access Token。

- **实时打印状态** —— 浏览器**直连**拓竹云 MQTT（`wss`）订阅打印机状态，展示进度/剩余时间/打印状态、喷嘴/热床/腔体温度、层数、打印速度、AMS 耗材、故障码（HMS）。不依赖后端常驻进程，可部署在 Vercel 等静态/Serverless 平台。
- **获取 Access Token** —— 手机号 + 短信验证码登录（含 Geetest 滑块人机验证）。此功能需要后端（访问拓竹中国区接口）。
- **其他** —— 中英文切换、PWA（可「添加到主屏幕」）、Token 本地暂存与自动恢复、移动端 / 平板 / 横屏适配。

## 功能与部署的关系

| 功能 | 是否需要后端 | 说明 |
|------|------------|------|
| 实时打印状态监控 | 否 | 浏览器直连 MQTT，纯前端即可 |
| 获取 Access Token | 是 | 后端用 `curl_cffi` 访问拓竹中国区接口 |

> 注意：获取 token 的接口访问拓竹**中国区**服务器。若后端部署在海外（如 Vercel 美国节点），可能因网络或地域策略导致失败。此时建议**本地运行获取一次 token**，再在任意部署的页面粘贴 token 查看状态。

## 安装

需要 Python 3.10+。

```bash
pip install -r requirements.txt
```

> `requirements.txt` 里的 Pillow 仅用于重新生成 PWA 图标（图标已生成在 `static/icons/`），默认注释，运行应用无需安装。

## 运行

```bash
python app.py
```

启动后控制台打印访问地址：

```
本机访问:  http://127.0.0.1:5000
手机访问:  http://<局域网IP>:5000   (需与电脑同一 Wi-Fi)
```

- 默认监听 `0.0.0.0`，同一局域网的手机可访问。
- 仅本机使用：`BAMBU_HOST=127.0.0.1 python app.py`。
- 自定义端口：`BAMBU_PORT=8080`。

## 使用流程

**已有 token：** 在「Bambu 打印状态」粘贴 Access Token → 验证 → 选择打印机 → 实时监控。token 与所选打印机暂存在浏览器，刷新或重进自动恢复。

**没有 token：** 点验证区下方「手机号登录获取 Token」→ 弹窗中输入手机号 → 获取验证码（完成滑块）→ 填验证码登录 → 「用此 Token 查看打印状态」。

## 技术说明

- 前端用 [MQTT.js](https://github.com/mqttjs/MQTT.js) 直连 `wss://cn.mqtt.bambulab.com:8084/mqtt`，订阅 `device/<序列号>/report`，对增量推送做字段合并。
- 后端 Flask + `curl_cffi`（伪装浏览器 TLS 指纹以通过拓竹中国区接口的反爬）；MQTT 用户名 `u_<uid>` 从 token 解析或经 preference 接口获取，密码即 token。
- 接口与 MQTT 协议参考自开源项目 [greghesp/ha-bambulab](https://github.com/greghesp/ha-bambulab)（pybambu），中国区将 `.com` 域名替换为 `.cn`。

## 安全提醒

- **Access Token 等同于账号登录凭证**，可控制你绑定的打印机。请勿分享、勿提交到公开仓库。
- token 仅暂存在你本机浏览器的 `localStorage`，可用页面「清除暂存」清除。
- 监听 `0.0.0.0` 时服务暴露到局域网，请在可信网络下使用。
- 监控时 token 会作为 MQTT 密码从浏览器直接发往拓竹服务器（与官方 App 行为一致）。

## 问题反馈

Bug 或建议请提 [Issues](https://github.com/swzsweet/Bambu-print-status-monitoring/issues)。

## 免责声明

本项目为个人学习与自用工具，与拓竹（Bambu Lab）官方无关。使用产生的一切后果由使用者自行承担。
