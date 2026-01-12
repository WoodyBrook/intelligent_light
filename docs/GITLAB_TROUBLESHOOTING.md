# GitLab 连接问题排查指南

## 问题：Connection reset by peer

### 可能的原因

1. **网络访问限制**
   - GitLab 服务器可能只允许内网访问
   - 需要 VPN 连接
   - 防火墙阻止了连接

2. **协议问题**
   - HTTP/HTTPS 可能被阻止
   - 需要使用 SSH 协议

3. **认证问题**
   - 需要配置 Personal Access Token
   - 需要配置 SSH 密钥

## 解决方案

### 方案 1：使用 SSH（推荐）

1. **检查是否已有 SSH 密钥**
   ```bash
   ls -la ~/.ssh/id_rsa.pub
   # 或
   ls -la ~/.ssh/id_ed25519.pub
   ```

2. **如果没有，生成 SSH 密钥**
   ```bash
   ssh-keygen -t ed25519 -C "jfei1197@gmail.com"
   # 或使用 RSA
   ssh-keygen -t rsa -b 4096 -C "jfei1197@gmail.com"
   ```

3. **将公钥添加到 GitLab**
   - 复制公钥内容：
     ```bash
     cat ~/.ssh/id_ed25519.pub
     # 或
     cat ~/.ssh/id_rsa.pub
     ```
   - 访问 GitLab：`https://gitlab.gotokepler.com/-/user_settings/ssh_keys`
   - 添加公钥

4. **使用 SSH URL 克隆**
   ```bash
   git clone git@gitlab.gotokepler.com:feijiajun/agentic_lamp.git
   ```

### 方案 2：检查 VPN 连接

如果 GitLab 服务器在内网，需要先连接 VPN：

1. 连接公司/组织 VPN
2. 然后重试克隆：
   ```bash
   git clone https://gitlab.gotokepler.com/feijiajun/agentic_lamp.git
   ```

### 方案 3：使用 Personal Access Token

1. **生成 Token**
   - 访问：`https://gitlab.gotokepler.com/-/user_settings/personal_access_tokens`
   - 创建 token，权限选择：`read_repository`, `write_repository`
   - 复制 token

2. **使用 Token 克隆**
   ```bash
   git clone https://oauth2:<YOUR_TOKEN>@gitlab.gotokepler.com/feijiajun/agentic_lamp.git
   ```

   或者：
   ```bash
   git clone https://gitlab.gotokepler.com/feijiajun/agentic_lamp.git
   # 用户名：feijiajun
   # 密码：输入你的 Personal Access Token
   ```

### 方案 4：检查网络和防火墙

1. **检查是否在公司网络**
   - 如果在公司网络，可能需要配置代理
   - 联系 IT 部门确认 GitLab 访问要求

2. **配置 Git 代理（如果需要）**
   ```bash
   # HTTP 代理
   git config --global http.proxy http://proxy.example.com:8080
   git config --global https.proxy https://proxy.example.com:8080
   
   # 取消代理
   git config --global --unset http.proxy
   git config --global --unset https.proxy
   ```

### 方案 5：测试连接

```bash
# 测试 SSH 连接
ssh -T git@gitlab.gotokepler.com

# 测试 HTTPS 连接（需要 token）
curl -I https://gitlab.gotokepler.com/feijiajun/agentic_lamp.git
```

## 快速诊断命令

```bash
# 1. 检查网络连通性
ping gitlab.gotokepler.com

# 2. 测试 HTTPS
curl -I https://gitlab.gotokepler.com

# 3. 测试 SSH
ssh -T git@gitlab.gotokepler.com

# 4. 检查 Git 配置
git config --list | grep -E "proxy|ssl|url"
```

## 常见错误及解决

### 错误：`Connection reset by peer`
- **原因**：网络连接被重置
- **解决**：使用 SSH 或检查 VPN

### 错误：`Permission denied (publickey)`
- **原因**：SSH 密钥未配置或未添加到 GitLab
- **解决**：添加 SSH 公钥到 GitLab

### 错误：`fatal: repository not found`
- **原因**：仓库不存在或没有访问权限
- **解决**：确认仓库 URL 和访问权限

## 推荐配置

对于内网 GitLab，推荐使用 SSH：

```bash
# 1. 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your-email@example.com"

# 2. 添加公钥到 GitLab

# 3. 测试连接
ssh -T git@gitlab.gotokepler.com

# 4. 使用 SSH URL
git remote set-url origin git@gitlab.gotokepler.com:feijiajun/agentic_lamp.git
```

---

**最后更新**: 2026-01-12
