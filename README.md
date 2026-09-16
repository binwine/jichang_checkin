# 签到😍<br/>
>只要机场网站''' Powered by SSPANEL ''',就可以进行签到。要确认是否是''' Powered by SSPANEL '''，在机场首页滑倒最底端就可以看到。例如：
![Y0}SY$J`8837H8T5GXM1DZY](https://user-images.githubusercontent.com/21276183/214764546-4f66333a-cb9b-420e-8260-697d26fb4547.png)
## 作用
>每天进行签到，获取额外的流量奖励

## 推送方式
### 企业微信

通过企业微信群机器人推送签到结果、登录失败或运行异常。参考 [BetterGI 企业微信通知实现](https://github.com/babalae/better-genshin-impact/pull/1106/files)，以 JSON 发送 `text` 消息。

在企业微信群中添加机器人，复制 Webhook 地址，将其中 `key=` 后的密钥保存到 GitHub Actions Secret **EMAIL**；也可以填写完整的 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的密钥` 地址。这里的 EMAIL 用于推送密钥，登录邮箱和密码仍填写在 CONFIG 中。

EMAIL 不设置或留空时关闭推送；原来的 SCKEY 不再使用。只有 HTTP 请求成功且接口返回 `errcode=0` 才记录推送成功，推送失败不会触发重复签到。

### QQ 官方机器人（私聊）

参考 [PR #3530](https://github.com/babalae/better-genshin-impact/pull/3530) 的官方 REST 文本推送，以及 [PR #3547](https://github.com/babalae/better-genshin-impact/pull/3547) 的消息格式。先用 AppID / AppSecret 获取 access_token，再向 `/v2/users/{openid}/messages` 发送 `msg_type=0` 的私聊消息。

在 Actions Secrets 中新增以下三项，全部配置后自动启用：

- `AppID`：QQ 开放平台机器人的 AppID。
- `AppSecret`：同一个机器人的 AppSecret。
- `openID`：接收者在该机器人下的 C2C OpenID，**不是 QQ 号码，也不是群 OpenID**。可在支持上述 PR 功能的 BetterGI 中配置同一个机器人，使用“绑定 OpenID”功能获取后填入；本脚本不监听绑定事件。

QQ 机器人须具备对应的私聊发送权限；平台的主动消息限制仍然适用，配置凭证不保证每次定时推送都能送达。HTTP 或接口报错会记录失败，且不会影响签到或企业微信推送。

消息格式如下，时间统一为北京时间（UTC+8）：

```text
[2026-09-15 21:30:00]
机场签到：账号0：签到成功
```

QQ 三项全部留空关闭 QQ 推送。可以只启用 QQ，也可以和企业微信同时启用。token 仅在本次脚本进程内缓存，密钥和 token 不写入文件或输出到日志；消息请求失败不自动重发，避免重复消息。

# 部署过程
 
1. 右上角Fork此仓库
2. 然后到`Settings`→`Secrets and variables`→`Actions` 新建以下机密：

| 参数            | 是否必须  | 内容  | 
|---------------| ------------ | ------------ |
| CONFIG        | 是  | 账号密码  |
| URL           | 是 | 机场地址，当前为 `` |
| EMAIL         | 否 | 企业微信群机器人 key 或完整 Webhook 地址，留空关闭推送 |
| APPID         | 否 | QQ 官方机器人的 AppID，启用 QQ 时必填 |
| APPSECRET | 否 | QQ 官方机器人的 AppSecret，启用 QQ 时必填 |
| OPENID    | 否 | 接收者的 C2C OpenID，启用 QQ 时必填 |
<br/>
<b>其中URL的值必须是机场网站的地址，例如：https://example.com</b>,尾部不要加''' / '''号 config写法：一行账号一行密码

3. 到`Actions`中创建一个workflow，运行一次，以后每天项目都会自动运行。<br/>
4. 最后，可以到 Run sign 查看签到情况；配置 EMAIL 后会将结果推送到企业微信群。

当前登录流程适配，不调用 GeeTest 验证码服务。两步验证码 `code` 留空，因此当前脚本适用于未启用两步验证的账号。

登录返回 `ret=2` 时，脚本会打开账号选择页，读取第一个“使用子账户登录”选项（主账号下一行），通过 `/user/redirect` 切换后再签到。无需在 CONFIG 中填写子账号密码；找不到子账号或切换后未进入用户中心时会停止签到。
