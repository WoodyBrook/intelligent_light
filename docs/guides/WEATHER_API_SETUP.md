# 和风天气 API 配置指南 (V2 - 适配 2024+ 新架构)

## 概述

项目已升级以适配和风天气最新的 API 架构，支持：
- ✅ 个性化 API Host (解决 404/NameResolutionError 问题)
- ✅ Header 鉴权 (更安全)
- ✅ 实时天气 & 未来预报

## 详细配置步骤

### 1. 注册与获取凭据

1. **访问控制台**：
   - 登录 [和风天气开发者控制台](https://console.qweather.com/)

2. **获取 API Key**：
   - 进入 **"项目管理"**
   - 确保创建了 **"Web API"** 类型的 Key (不要选 SDK)
   - 复制 **KEY**

3. **获取 API Host (关键)**：
   - 在项目管理页面，点击您的项目名称
   - 在项目详情中，找到 **API Host** 字段
   - 例如：`abcxyz.qweatherapi.com` (这是您专属的调用域名)

### 2. 配置环境变量

在项目根目录创建或编辑 `.env` 文件，填入以下两项：

```bash
# 和风天气 API Key
QWEATHER_API_KEY=your_api_key_here

# 您的专属 API Host (不带 https://)
QWEATHER_API_HOST=abcxyz.qweatherapi.com
```

### 3. 重启应用

配置完成后，重启 demo 应用即可使用真实天气数据。

## 使用示例

### 实时天气查询

- 用户："今天天气怎么样？"
- 用户："上海天气"
- 系统：返回实时天气数据

## API 说明 (V2 更新)

新版代码不再使用硬编码的 `api.qweather.com`，而是通过环境变量 `QWEATHER_API_HOST` 动态构建请求 URL。同时鉴权方式由 Query 参数改为 `X-QW-Api-Key` Header。

### 降级方案

- 如果未配置 `QWEATHER_API_KEY`，系统自动降级为 **模拟数据**。
- 如果未配置 `QWEATHER_API_HOST`，系统默认使用 `devapi.qweather.com` (可能导致连接失败)。

## 故障排查

### 问题：运行诊断脚本报错 "NameResolutionError" 或 404

**原因**：使用了错误的 Host。
**解决**：
1. 运行 `python scripts/diagnose_weather.py`
2. 检查输出中的 `API Host` 是否与控制台一致。
3. 确保 `.env` 中 `QWEATHER_API_HOST` 设置正确。

### 问题：API 调用失败 (401/403)

**原因**：
- Key 类型选错（需选 Web API）
- 免费额度用尽

---

**配置完成后，即可获取真实的天气数据！** 🌤️
