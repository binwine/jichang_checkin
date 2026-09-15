import requests, json, os, re
from html.parser import HTMLParser
from urllib.parse import urlparse

# 机场的地址
url = os.environ.get('URL')
# 配置用户名（一般是邮箱）

config = os.environ.get('CONFIG')
# server酱
SCKEY = os.environ.get('SCKEY')

login_url = '{}/auth/login'.format(url)
check_url = '{}/user/checkin'.format(url)

def build_login_data(user, pwd):
        """按 onesy3 登录页构造表单，未启用两步验证时 code 留空。"""
        return {
                'email': user,
                'passwd': pwd,
                'code': '',
                'remember_me': 'week',
        }


def login_succeeded(response):
        """ret=2 表示认证成功，但仍需选择子账号。"""
        return (
                response.get('phase') == 'authenticated'
                or str(response.get('ret')) in ('1', '2')
        )

class AccountParser(HTMLParser):
        """读取账号选择页中 relogin 按钮的邮箱及显示文字。"""
        def __init__(self):
                super().__init__()
                self.accounts = []
                self.current = None
                self.div_depth = 0

        def handle_starttag(self, tag, attrs):
                if tag != 'div':
                        return
                if self.current is not None:
                        self.div_depth += 1
                        return
                onclick = dict(attrs).get('onclick', '')
                match = re.fullmatch(r'''\s*relogin\(\s*(['"])([^'"]+)\1\s*\)\s*;?\s*''', onclick)
                if match:
                        self.current = {'email': match.group(2), 'text': ''}
                        self.div_depth = 1

        def handle_data(self, data):
                if self.current is not None:
                        self.current['text'] += data

        def handle_endtag(self, tag):
                if tag == 'div' and self.current is not None:
                        self.div_depth -= 1
                        if self.div_depth == 0:
                                self.accounts.append(self.current)
                                self.current = None


def find_subaccount(html):
        parser = AccountParser()
        parser.feed(html)
        for account in parser.accounts:
                if '使用子账户登录' in account['text']:
                        return account['email']
        raise ValueError('账号选择页未找到子账号，停止签到，避免误签主账号')


def select_subaccount(session, header):
        """对应选择页的 relogin(email)：以普通表单切换到第一个子账号。"""
        accounts_url = f'{url}/user/accounts'
        page_header = {key: value for key, value in header.items()
                       if key.lower() != 'x-requested-with'}
        accounts_page = session.get(url=accounts_url, headers=page_header, timeout=30)
        accounts_page.raise_for_status()
        email = find_subaccount(accounts_page.text)
        print('检测到主／子账号选择页，正在进入第一个子账号...')
        page_header['referer'] = accounts_url
        switched = session.post(
                url=f'{url}/user/redirect', headers=page_header,
                data={'email': email}, timeout=30,
        )
        switched.raise_for_status()
        destination = urlparse(switched.url)
        origin = urlparse(url)
        if (destination.scheme, destination.netloc) != (origin.scheme, origin.netloc) or destination.path.rstrip('/') != '/user':
                raise ValueError('子账号切换后未进入用户中心，停止签到')
        print('已进入子账号用户中心')


def sign(order,user,pwd):
        session = requests.session()
        global url,SCKEY
        header = {
        'origin': url,
        'referer': login_url,
        'x-requested-with': 'XMLHttpRequest',
        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
        }
        try:
                print(f'===账号{order}进行登录...===')
                print(f'账号：{user}')

                # 先访问登录页，建立与浏览器一致的会话。
                login_page = session.get(url=login_url, headers=header, timeout=30)
                login_page.raise_for_status()
                data = build_login_data(user, pwd)

                login_response = session.post(
                        url=login_url, headers=header, data=data, timeout=30
                )
                login_response.raise_for_status()
                print(login_response.text)
                response = login_response.json()
                message = response.get('msg', '登录接口未返回提示信息')
                print(message)

                if not login_succeeded(response):
                        print(f'登录失败: {message}')
                        content = f'登录失败: {message}'
                        if SCKEY != '':
                                push_url = 'https://sctapi.ftqq.com/{}.send?title=机场签到&desp={}'.format(SCKEY, content)
                                requests.post(url=push_url)
                                print('推送成功')
                        return

                if str(response.get('ret')) == '2':
                        select_subaccount(session, header)

                # 使用切换后的会话进行签到。
                header['referer'] = f'{url}/user'
                check_response = session.post(url=check_url, headers=header, timeout=30)
                check_response.raise_for_status()
                res2 = check_response.text
                print(res2)
                result = json.loads(res2)
                print(result['msg'])
                content = result['msg']
                # 进行推送
                if SCKEY != '':
                        push_url = 'https://sctapi.ftqq.com/{}.send?title=机场签到&desp={}'.format(SCKEY, content)
                        requests.post(url=push_url)
                        print('推送成功')
        except Exception as ex:
                content = '签到失败'
                print(content)
                print("出现如下异常%s"%ex)
                if SCKEY != '':
                        push_url = 'https://sctapi.ftqq.com/{}.send?title=机场签到&desp={}'.format(SCKEY, content)
                        requests.post(url=push_url)
                        print('推送成功')
        print('===账号{order}签到结束===\n'.format(order=order))
if __name__ == '__main__':
        configs = config.splitlines()
        if len(configs) %2 != 0 or len(configs) == 0:
                print('配置文件格式错误')
                exit()
        user_quantity = len(configs)
        user_quantity = user_quantity // 2
        for i in range(user_quantity):
                user = configs[i*2]
                pwd = configs[i*2+1]
                sign(i,user,pwd)
