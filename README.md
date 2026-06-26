# Bambu 打印状态 & Access Token 获取

一个本地运行的网页应用，用于：

1. **获取拓竹（Bambu Lab）中国区账号的 Access Token** —— 手机号 + 短信验证码登录（含 Geetest 滑块人机验证）。
2. **实时查看打印机状态** —— 用 token 通过拓竹云 MQTT 订阅打印机状态，展示喷嘴/热床/腔体温度、打印进度、剩余时间、层数、打印速度、AMS 耗材、故障码（HMS）。

支持 PWA（可「添加到主屏幕」当独立应用使用）、本地暂存 token、移动端适配。

## 截图

- **打印状态页**：输入 token → 验证 → 选择打印机 → 实时监控
- **获取 Token**：页面底部入口，手机号 + 验证码登录

## 安装

需要 Python 3.10+。

```bash
pip install -r requirements.txt
```

> `requirements.txt` 中的 Pillow 仅用于重新生成 PWA 图标，运行应用本身不需要（图标已生成在 `static/icons/`）。

## 运行

```bash
python app.py
```

启动后控制台会打印访问地址：

```
本机访问:  http://127.0.0.1:5000
手机访问:  http://<局域网IP>:5000   (需与电脑同一 Wi-Fi)
```

- 默认监听 `0.0.0.0`，同一局域网的手机可访问。
- 仅想本机使用：设置环境变量 `BAMBU_HOST=127.0.0.1` 再启动。
- 自定义端口：`BAMBU_PORT=8080`。

## 使用流程

### 查看打印状态（已有 token）
1. 打开页面，在「Bambu 打印状态」卡片粘贴 Access Token。
2. 点「验证 Token」，验证通过后列出账号下的打印机。
3. 点选一台打印机，开始实时监控。
4. token 与所选打印机会暂存在浏览器本地，刷新或重进自动恢复。

### 获取 token（没有 token）
1. 点页面底部「没有 Token？点此获取」。
2. 输入中国区手机号 → 获取验证码（需完成滑块验证）→ 填入验证码 → 登录。
3. 获取到 token 后可一键「用此 Token 查看打印状态」。

## 技术说明

- 后端：Flask；用 `curl_cffi` 伪装浏览器 TLS 指纹以通过拓竹中国区接口的反爬；`paho-mqtt` 订阅打印机状态；通过 SSE（Server-Sent Events）把实时状态推送到浏览器。
- 接口与 MQTT 协议参考自开源项目 [greghesp/ha-bambulab](https://github.com/greghesp/ha-bambulab)（pybambu），中国区将 `.com` 域名替换为 `.cn`。

## 安全提醒

- **Access Token 等同于账号登录凭证**，可控制你绑定的打印机。请勿分享、勿提交到公开仓库。
- token 仅暂存在你本机浏览器的 `localStorage`，可用页面上的「清除暂存」清除。
- 当监听 `0.0.0.0` 时，服务会暴露到局域网，请在可信网络环境下使用。
- 通过局域网 IP 以 HTTP 访问时，浏览器会禁用 Service Worker（非安全上下文），此时实时监控正常，但 PWA 安装/离线缓存受限——完整 PWA 需要 HTTPS 或通过 `localhost` 访问。

## 免责声明

本项目为个人学习与自用工具，与拓竹（Bambu Lab）官方无关。使用产生的一切后果由使用者自行承担。
