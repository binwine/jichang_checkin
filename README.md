# 通用机场签到😍<br/>
>只要机场网站''' Powered by SSPANEL ''',就可以进行签到。要确认是否是''' Powered by SSPANEL '''，在机场首页滑倒最底端就可以看到。例如：
![Y0}SY$J`8837H8T5GXM1DZY](https://user-images.githubusercontent.com/21276183/214764546-4f66333a-cb9b-420e-8260-697d26fb4547.png)
## 作用
>每天进行签到，获取额外的流量奖励

## 推送方式
通过企业微信群机器人推送签到结果、登录失败或运行异常。参考 [BetterGI 企业微信通知实现](https://github.com/babalae/better-genshin-impact/pull/1106/files)，以 JSON 发送 `text` 消息。

在企业微信群中添加机器人，复制 Webhook 地址，将其中 `key=` 后的密钥保存到 GitHub Actions Secret **EMAIL**；也可以填写完整的 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的密钥` 地址。这里的 EMAIL 用于推送密钥，登录邮箱和密码仍填写在 CONFIG 中。

EMAIL 不设置或留空时关闭推送；原来的 SCKEY 不再使用。只有 HTTP 请求成功且接口返回 `errcode=0` 才记录推送成功，推送失败不会触发重复签到。

# 部署过程
 
1. 右上角Fork此仓库
2. 然后到`Settings`→`Secrets and variables`→`Actions` 新建以下机密：

| 参数   | 是否必须  | 内容  | 
| ------------ | ------------ | ------------ |
| CONFIG| 是  | 账号密码  |
| URL | 是 | 机场地址，当前为 `` |
| EMAIL | 否 | 企业微信群机器人 key 或完整 Webhook 地址，留空关闭推送 |
<br/>
<b>其中URL的值必须是机场网站的地址，例如：https://example.com</b>,尾部不要加''' / '''号 config写法：一行账号一行密码

3. 到`Actions`中创建一个workflow，运行一次，以后每天项目都会自动运行。<br/>
4. 最后，可以到 Run sign 查看签到情况；配置 EMAIL 后会将结果推送到企业微信群。

当前登录流程适配，不调用 GeeTest 验证码服务。两步验证码 `code` 留空，因此当前脚本适用于未启用两步验证的账号。

登录返回 `ret=2` 时，脚本会打开账号选择页，读取第一个“使用子账户登录”选项（主账号下一行），通过 `/user/redirect` 切换后再签到。无需在 CONFIG 中填写子账号密码；找不到子账号或切换后未进入用户中心时会停止签到。
