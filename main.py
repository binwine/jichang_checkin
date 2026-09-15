import requests, json, os

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
        """兼容新版 phase 响应和旧版 ret 响应。"""
        return (
                response.get('phase') == 'authenticated'
                or str(response.get('ret')) == '1'
        )

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

                # 进行签到
                res2 = session.post(url=check_url,headers=header).text
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
