# -*- coding: utf-8 -*-
"""
拓竹（Bambu Lab）中国区 Access Token 获取 - 网页版

手机号 + 短信验证码登录，获取 accessToken。
仅本地运行：python app.py 然后浏览器打开 http://127.0.0.1:5000

接口来源：开源项目 greghesp/ha-bambulab (pybambu)，中国区将 .com 替换为 .cn
"""

import json
import os
import base64
import socket
from curl_cffi import requests as creq
from curl_cffi.requests.exceptions import Timeout as CurlTimeout, RequestException as CurlRequestException
from flask import (
    Flask, request, jsonify, render_template, send_from_directory,
)

app = Flask(__name__)

# curl_cffi 伪装真实浏览器的 TLS 指纹。
# 拓竹中国区接口（bambulab.cn）前置了反爬，普通 requests 的指纹会被识别后挂起，
# 表现为请求一直“卡住”不返回。必须用 curl_cffi impersonate 浏览器才能正常通信。
IMPERSONATE = "chrome"
TIMEOUT = 30

# ---- 中国区接口地址 ----
LOGIN_URL = "https://api.bambulab.cn/v1/user-service/user/login"
# 注意：短信验证码接口域名不带 api. 前缀，且路径多一段 /api（与 login 结构不同）
SMS_CODE_URL = "https://bambulab.cn/api/v1/user-service/user/sendsmscode"
# 账号下绑定的设备列表
BIND_URL = "https://api.bambulab.cn/v1/iot-service/api/user/bind"
# 用户偏好接口：token 非 JWT 时用它拿 uid（拼成 MQTT 用户名 u_<uid>）
PREFERENCE_URL = "https://api.bambulab.cn/v1/design-user-service/my/preference"

# 模拟 Bambu 官方客户端的请求头，降低被 Cloudflare 拦截的概率
HEADERS = {
    "User-Agent": "bambu_network_agent/01.09.05.01",
    "X-BBL-Client-Name": "OrcaSlicer",
    "X-BBL-Client-Type": "slicer",
    "X-BBL-Client-Version": "01.09.05.51",
    "X-BBL-Language": "zh-CN",
    "X-BBL-OS-Type": "linux",
    "X-BBL-OS-Version": "6.2.0",
    "X-BBL-Agent-Version": "01.09.05.01",
    "X-BBL-Executable-info": "{}",
    "X-BBL-Agent-OS-Type": "linux",
    "accept": "application/json",
    "Content-Type": "application/json",
}


def _post(url: str, payload: dict):
    """统一发送 POST，返回 (status_code, json_or_text)。"""
    resp = creq.post(url, headers=HEADERS, json=payload, impersonate=IMPERSONATE, timeout=TIMEOUT)
    if resp.status_code == 403 and "cloudflare" in resp.text.lower():
        raise RuntimeError("被 Cloudflare 拦截，请稍后重试或更换网络环境。")
    try:
        return resp.status_code, resp.json()
    except json.JSONDecodeError:
        return resp.status_code, resp.text


@app.route("/")
def index():
    return render_template("index.html")


# PWA：service worker 和 manifest 必须从根作用域提供
@app.route("/sw.js")
def service_worker():
    resp = send_from_directory("static", "sw.js", mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory("static", "manifest.webmanifest",
                               mimetype="application/manifest+json")


@app.route("/api/captcha-id", methods=["POST"])
def captcha_id():
    """第 1 步：向发码接口发起请求，拿到 Geetest 的 captchaId。
    中国区发短信前强制人机验证：服务器会返回 418 + captchaId，
    前端用它初始化 Geetest 滑块，用户滑动通过后再带验证票据发码。"""
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    if not phone:
        return jsonify(ok=False, error="请输入手机号"), 400

    try:
        status, body = _post(SMS_CODE_URL, {"phone": phone, "type": "codeLogin"})
        if not isinstance(body, dict):
            return jsonify(ok=False, error=f"返回异常（HTTP {status}）：{body}"), 502

        # 正常情况下会返回 418 + captchaId
        captcha = body.get("captchaId")
        if captcha:
            return jsonify(ok=True, captcha_id=captcha)

        # 极少数情况下可能直接成功（无需验证）
        if status == 200:
            return jsonify(ok=True, sent=True, message="验证码已发送，请查收短信。")

        return jsonify(ok=False, error=f"未获取到验证码挑战（HTTP {status}）：{body}"), 502
    except RuntimeError as e:
        return jsonify(ok=False, error=str(e)), 502
    except CurlTimeout:
        return jsonify(ok=False, error="连接拓竹服务器超时，请检查网络后重试。"), 504
    except CurlRequestException as e:
        return jsonify(ok=False, error=f"网络请求失败：{e}"), 502


@app.route("/api/send-code", methods=["POST"])
def send_code():
    """第 2 步：带上 Geetest 滑块通过后的验证票据，正式发送短信验证码。"""
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    captcha = data.get("captcha") or {}
    if not phone:
        return jsonify(ok=False, error="请输入手机号"), 400
    if not captcha.get("lot_number"):
        return jsonify(ok=False, error="请先完成人机验证（滑块）。"), 400

    # Geetest V4 通过后回传的票据字段
    payload = {
        "phone": phone,
        "type": "codeLogin",
        "captchaId": captcha.get("captcha_id", ""),
        "lot_number": captcha.get("lot_number", ""),
        "captcha_output": captcha.get("captcha_output", ""),
        "pass_token": captcha.get("pass_token", ""),
        "gen_time": captcha.get("gen_time", ""),
    }

    try:
        status, body = _post(SMS_CODE_URL, payload)
        if status != 200:
            return jsonify(ok=False, error=f"发送验证码失败（HTTP {status}）：{body}"), 502

        return jsonify(ok=True, message="验证码已发送，请查收短信。")
    except RuntimeError as e:
        return jsonify(ok=False, error=str(e)), 502
    except CurlTimeout:
        return jsonify(ok=False, error="连接拓竹服务器超时，请检查网络后重试。"), 504
    except CurlRequestException as e:
        return jsonify(ok=False, error=f"网络请求失败：{e}"), 502


@app.route("/api/login", methods=["POST"])
def login():
    """第 3 步：用 手机号 + 验证码 换取 accessToken。"""
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()
    if not phone or not code:
        return jsonify(ok=False, error="请输入手机号和验证码"), 400

    try:
        status, body = _post(LOGIN_URL, {"account": phone, "code": code})
        if not isinstance(body, dict):
            return jsonify(ok=False, error=f"登录返回异常（HTTP {status}）：{body}"), 502

        if status == 400:
            err = body.get("code")
            if err == 1:
                return jsonify(ok=False, error="验证码已过期，请重新获取。"), 400
            if err == 2:
                return jsonify(ok=False, error="验证码错误，请重新输入。"), 400
            return jsonify(ok=False, error=f"登录失败：{body}"), 400

        if status != 200:
            return jsonify(ok=False, error=f"登录失败（HTTP {status}）：{body}"), 502

        token = body.get("accessToken", "")
        if not token:
            return jsonify(ok=False, error=f"登录成功但未返回 accessToken：{body}"), 502

        return jsonify(ok=True, access_token=token)
    except RuntimeError as e:
        return jsonify(ok=False, error=str(e)), 502
    except CurlTimeout:
        return jsonify(ok=False, error="连接拓竹服务器超时，请检查网络后重试。"), 504
    except CurlRequestException as e:
        return jsonify(ok=False, error=f"网络请求失败：{e}"), 502


@app.route("/api/devices", methods=["POST"])
def devices():
    """（兼容保留）用 access token 获取账号下绑定的打印机列表。
    新前端已改用 /api/verify-token。"""
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    if not token:
        return jsonify(ok=False, error="请输入 Access Token"), 400

    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    try:
        resp = creq.get(BIND_URL, headers=headers, impersonate=IMPERSONATE, timeout=TIMEOUT)
        if resp.status_code == 401:
            return jsonify(ok=False, error="Token 无效或已过期（401）。"), 401
        try:
            body = resp.json()
        except json.JSONDecodeError:
            return jsonify(ok=False, error=f"返回非 JSON（HTTP {resp.status_code}）：{resp.text[:300]}"), 502
        if resp.status_code != 200:
            return jsonify(ok=False, error=f"获取失败（HTTP {resp.status_code}）：{body}"), 502
        return jsonify(ok=True, devices=body.get("devices", []) or [])
    except CurlTimeout:
        return jsonify(ok=False, error="连接拓竹服务器超时，请检查网络后重试。"), 504
    except CurlRequestException as e:
        return jsonify(ok=False, error=f"网络请求失败：{e}"), 502


# ========== Token 解析 ==========

def parse_username_from_token(token: str):
    """从 access token(JWT) 中解析出 MQTT 用户名 u_<uid>。
    JWT 第二段(payload) base64 解码后含 username 字段。"""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        seg = parts[1]
        seg += "=" * ((4 - len(seg) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(seg))
        return payload.get("username")
    except Exception:
        return None


def fetch_username_via_preference(token: str):
    """token 不是 JWT（中国区常见的不透明 token）时，
    调 preference 接口拿 uid，拼成 MQTT 用户名 u_<uid>。"""
    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    try:
        resp = creq.get(PREFERENCE_URL, headers=headers, impersonate=IMPERSONATE, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        uid = resp.json().get("uid")
        return f"u_{uid}" if uid is not None else None
    except Exception:
        return None


def resolve_username(token: str):
    """先尝试 JWT 解析，失败再回退到 preference 接口。"""
    return parse_username_from_token(token) or fetch_username_via_preference(token)


@app.route("/api/verify-token", methods=["POST"])
def verify_token():
    """独立的 token 验证端点：校验 token 并返回账号下的打印机列表（含序列号）。"""
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    if not token:
        return jsonify(ok=False, error="请输入 Access Token"), 400

    username = resolve_username(token)

    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    try:
        resp = creq.get(BIND_URL, headers=headers, impersonate=IMPERSONATE, timeout=TIMEOUT)
        if resp.status_code == 401:
            return jsonify(ok=False, error="Token 无效或已过期（401）。"), 401
        try:
            body = resp.json()
        except json.JSONDecodeError:
            return jsonify(ok=False, error=f"返回非 JSON（HTTP {resp.status_code}）：{resp.text[:300]}"), 502
        if resp.status_code != 200:
            return jsonify(ok=False, error=f"验证失败（HTTP {resp.status_code}）：{body}"), 502

        devices_list = body.get("devices", []) or []
        simplified = [
            {
                "name": d.get("name"),
                "dev_id": d.get("dev_id"),  # 序列号，MQTT 订阅需要
                "online": d.get("online"),
                "dev_product_name": d.get("dev_product_name"),
                "dev_model_name": d.get("dev_model_name"),
                "print_status": d.get("print_status"),
                "nozzle_diameter": d.get("nozzle_diameter"),
            }
            for d in devices_list
        ]
        return jsonify(ok=True, username=username, count=len(simplified), devices=simplified)
    except CurlTimeout:
        return jsonify(ok=False, error="连接拓竹服务器超时，请检查网络后重试。"), 504
    except CurlRequestException as e:
        return jsonify(ok=False, error=f"网络请求失败：{e}"), 502


if __name__ == "__main__":
    # 默认监听 0.0.0.0，方便同一局域网的手机访问。
    # 安全提醒：这会把服务暴露到局域网，同网络的人可访问你的页面并操作你的 token。
    # 如只想本机使用，设置环境变量 BAMBU_HOST=127.0.0.1。
    host = os.environ.get("BAMBU_HOST", "0.0.0.0")
    port = int(os.environ.get("BAMBU_PORT", "5000"))

    if host == "0.0.0.0":
        lan_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass
        print("=" * 56)
        print("  本机访问:  http://127.0.0.1:%d" % port)
        print("  手机访问:  http://%s:%d  (需与电脑同一 Wi-Fi)" % (lan_ip, port))
        print("  [!] 服务已暴露到局域网，token 等同账号凭证，注意环境安全。")
        print("  仅本机使用请设环境变量 BAMBU_HOST=127.0.0.1")
        print("=" * 56)

    # threaded=True：SSE 长连接需要多线程，否则会阻塞其它请求
    app.run(host=host, port=port, debug=False, threaded=True)
