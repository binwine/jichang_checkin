import getpass
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
import tkinter as tk
from tkinter import messagebox

import websocket


TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
GATEWAY_URL = "https://api.sgroup.qq.com/gateway"
BIND_TIMEOUT = 120  # READY 后等待绑定的秒数


def request_json(url, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"QQBot {token}"

    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # 仅显示错误码，避免把凭证等响应内容写入终端日志。
        raw = exc.read()
        detail = ""
        try:
            error = json.loads(raw)
            detail = f"，业务码：{error.get('code', error.get('errcode', '未知'))}"
        except (ValueError, AttributeError):
            pass
        raise RuntimeError(
            f"HTTP 请求失败：{exc.code}{detail}。请检查凭证和机器人权限。"
        ) from None


def bind_openid(app_id, app_secret):
    print("正在获取访问凭证……")
    result = request_json(
        TOKEN_URL,
        {"appId": app_id, "clientSecret": app_secret},
    )
    token = result.get("access_token")
    if not token:
        raise RuntimeError("未返回 access_token，请检查 AppID 和 AppSecret。")

    print("正在获取网关地址……")
    gateway = request_json(GATEWAY_URL, token=token).get("url")
    if not isinstance(gateway, str) or not gateway.startswith("wss://"):
        raise RuntimeError("未返回有效的 WSS 网关地址。")

    # 只接受包含本次随机码的完整绑定指令。
    command = f"绑定 {secrets.token_hex(4)}"
    socket = None
    sequence = None
    interval = None
    next_heartbeat = float("inf")
    awaiting_ack = False
    ready = False

    # 连接后先给握手和鉴权 30 秒。
    deadline = time.monotonic() + 30

    try:
        print("正在连接 QQ 网关……")
        socket = websocket.create_connection(gateway, timeout=15)
        socket.settimeout(1)

        def send(op, data):
            socket.send(json.dumps(
                {"op": op, "d": data},
                ensure_ascii=False,
            ))

        while True:
            now = time.monotonic()
            if now >= deadline:
                if ready:
                    raise RuntimeError("绑定超时，请重新运行并发送新的绑定码。")
                raise RuntimeError("网关握手或鉴权超时，请稍后重试。")

            if interval is not None and now >= next_heartbeat:
                if awaiting_ack:
                    raise RuntimeError("QQ 网关未确认心跳，请重新运行。")
                send(1, sequence)
                awaiting_ack = True
                next_heartbeat = now + interval

            try:
                raw = socket.recv()
            except websocket.WebSocketTimeoutException:
                continue

            if not raw:
                raise RuntimeError("QQ 网关已关闭连接，请检查权限后重试。")

            event = json.loads(raw)
            op = event.get("op")
            data = event.get("d")

            if isinstance(event.get("s"), int):
                sequence = event["s"]

            if op == 10:  # Hello
                if interval is not None:
                    raise RuntimeError("收到重复 Hello，请重新运行。")

                interval = float(data["heartbeat_interval"]) / 1000
                if interval <= 0:
                    raise RuntimeError("网关返回的心跳间隔无效。")

                next_heartbeat = time.monotonic() + interval
                send(2, {
                    "token": f"QQBot {token}",
                    "intents": 1 << 25,  # GROUP_AND_C2C_EVENT
                    "shard": [0, 1],
                })

            elif op == 11:  # Heartbeat ACK
                awaiting_ack = False

            elif op == 1:  # 服务端要求立即发送心跳
                send(1, sequence)

            elif op == 7:
                raise RuntimeError("网关要求重新连接，请重新运行脚本。")

            elif op == 9:
                raise RuntimeError(
                    "网关拒绝鉴权或会话无效，请检查凭证及 "
                    "GROUP_AND_C2C_EVENT 单聊事件权限。"
                )

            elif op == 0:
                event_type = event.get("t")

                if event_type == "READY" and not ready:
                    ready = True
                    deadline = time.monotonic() + BIND_TIMEOUT
                    print("\n连接成功！")
                    print(f"请在 {BIND_TIMEOUT} 秒内私聊机器人，发送以下完整内容：")
                    print(f"\n{command}\n")
                    print("等待消息……（Ctrl+C 取消）")

                elif ready and event_type == "C2C_MESSAGE_CREATE":
                    data = data or {}
                    content = data.get("content", "")
                    if not isinstance(content, str):
                        continue
                    if content.strip() != command:
                        continue

                    author = data.get("author") or {}
                    open_id = author.get("user_openid")

                    if isinstance(open_id, str) and open_id:
                        return open_id

                    raise RuntimeError("收到绑定消息，但缺少 user_openid。")

                # 不通过 FRIEND_ADD 自动绑定，避免绑定到其他用户。

    finally:
        if socket is not None:
            try:
                socket.close(timeout=2)
            except Exception:
                pass


def main():
    def on_submit():
        """处理提交按钮点击事件"""
        app_id = entry_app_id.get().strip()
        app_secret = entry_app_secret.get().strip()

        if not app_id or not app_secret:
            messagebox.showwarning("输入错误", "AppID 和 AppSecret 都不能为空！")
            return

        # 禁用按钮防止重复提交
        btn_submit.config(state=tk.DISABLED)
        root.update()

        try:
            open_id = bind_openid(app_id, app_secret)
            # 成功后显示 OpenID
            messagebox.showinfo("获取成功", f"你的 OpenID 是：\n\n{open_id}\n\n已复制到剪贴板。")
            root.clipboard_clear()
            root.clipboard_append(open_id)
            root.destroy() # 关闭窗口
        except Exception as exc:
            # 失败后显示错误信息
            messagebox.showerror("获取失败", f"错误信息：\n{exc}")
            btn_submit.config(state=tk.NORMAL) # 恢复按钮

    # --- 创建主窗口 ---
    root = tk.Tk()
    root.title("QQ 机器人 OpenID 获取工具")
    # 设置窗口大小并居中
    window_width = 350
    window_height = 150
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    # 禁止调整窗口大小
    root.resizable(False, False)

    # --- 创建界面元素 ---
    # 使用 grid 布局管理器
    root.columnconfigure(1, weight=1)

    tk.Label(root, text="AppID:").grid(row=0, column=0, padx=10, pady=(20, 5), sticky="e")
    entry_app_id = tk.Entry(root, width=30)
    entry_app_id.grid(row=0, column=1, padx=10, pady=(20, 5), sticky="ew")

    tk.Label(root, text="AppSecret:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
    entry_app_secret = tk.Entry(root, width=30, show="*") # 密码输入框
    entry_app_secret.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    btn_submit = tk.Button(root, text="获取 OpenID", command=on_submit, width=20)
    btn_submit.grid(row=2, column=0, columnspan=2, pady=20)

    # 让回车键也能触发提交
    root.bind('<Return>', lambda event: on_submit())

    # 启动主事件循环
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消。")
        sys.exit(130)
    except Exception as exc:
        print(f"\n失败：{exc}")
        sys.exit(1)