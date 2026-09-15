"""QQ 官方 C2C 文本推送，参考 BetterGI PR #3530 和 #3547。"""

import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests


class QQNotifier:
    TOKEN_URL = 'https://bots.qq.com/app/getAppAccessToken'
    API_BASE = 'https://api.sgroup.qq.com/v2/users'

    def __init__(self, app_id='', app_secret='', open_id=''):
        self.app_id = app_id.strip()
        self.app_secret = app_secret.strip()
        self.open_id = open_id.strip()
        self._token = None
        self._expires_at = 0

    def _get_token(self):
        if self._token and time.monotonic() < self._expires_at:
            return self._token
        self._token = None
        started_at = time.monotonic()
        response = requests.post(
            self.TOKEN_URL,
            json={'appId': self.app_id, 'clientSecret': self.app_secret},
            timeout=30, allow_redirects=False,
        )
        if response.status_code != 200:
            raise ValueError('获取 QQ token 的 HTTP 请求失败')
        result = response.json()
        token = result.get('access_token')
        lifetime = int(result.get('expires_in', 0))
        if not isinstance(token, str) or not token.strip() or lifetime <= 0:
            raise ValueError('获取 QQ token 的响应无效')
        self._token = token
        # 提前刷新；短有效期的 token 不跨消息缓存。
        self._expires_at = started_at + max(lifetime - 60, 0)
        return token

    def send(self, content):
        if not any((self.app_id, self.app_secret, self.open_id)):
            return False
        if not all((self.app_id, self.app_secret, self.open_id)):
            print('QQ 推送未发送：请同时配置 QQ_APP_ID、QQ_APP_SECRET、QQ_OPEN_ID')
            return False
        try:
            token = self._get_token()
            timestamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
            response = requests.post(
                f'{self.API_BASE}/{quote(self.open_id, safe="")}/messages',
                headers={'Authorization': f'QQBot {token}'},
                json={'msg_type': 0, 'content': f'[{timestamp}]\n机场签到：{content}'},
                timeout=30, allow_redirects=False,
            )
            if not 200 <= response.status_code < 300:
                if response.status_code == 401:
                    self._token = None
                print(f'QQ 推送失败：HTTP {response.status_code}，请检查凭证、OpenID 及机器人发消息权限')
                return False
            result = response.json()
            if result.get('code') not in (None, 0) or not result.get('id'):
                print('QQ 推送失败：接口未返回成功消息 ID，请检查机器人配置及发送限制')
                return False
            print('QQ 推送成功')
            return True
        except Exception as ex:
            # 不输出异常正文或 API 响应，避免泄露 AppSecret、token、OpenID。
            print(f'QQ 推送失败：{type(ex).__name__}，请检查配置及网络')
            return False
        # 消息发送不自动重试：请求超时不代表未送达，避免重复推送。
