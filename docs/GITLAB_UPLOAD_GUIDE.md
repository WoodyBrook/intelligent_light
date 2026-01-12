# GitLab 上传指南

本文档说明哪些文件应该上传到 GitLab 仓库，哪些文件应该被忽略。

## ✅ 应该上传的文件

### 1. 源代码文件
- ✅ `src/` - 所有源代码目录
  - `__init__.py`
  - `*.py` 所有 Python 模块
- ✅ `config/` - 配置文件
  - `__init__.py`
  - `prompts.py`
- ✅ `demo/` - Streamlit 演示应用
  - `app.py`
  - `utils.py`
  - `scenarios.py`
- ✅ `scripts/` - 工具脚本
  - `*.py` 所有脚本文件
- ✅ `tests/` - 测试文件
  - `__init__.py`
  - `test_*.py` 所有测试文件
  - `unit/` 单元测试目录

### 2. 项目配置文件
- ✅ `main.py` - 主入口文件
- ✅ `requirements.txt` - Python 依赖列表
- ✅ `README.md` - 项目说明文档
- ✅ `.gitignore` - Git 忽略规则
- ✅ `.cursorrules` - Cursor IDE 规则（项目规范）
- ✅ `pyrightconfig.json` - 类型检查配置
- ✅ `env-example.txt` - 环境变量配置模板（**重要：不包含真实 API keys**）

### 3. 文档文件
- ✅ `docs/` - 所有文档目录
  - `architecture/` - 架构文档
  - `guides/` - 使用指南
  - `implementation/` - 实现文档
  - `plans/` - 计划文档
  - `prd/` - 产品需求文档
  - `summaries/` - 总结文档
  - `*.md` - 所有 Markdown 文档

### 4. 归档文件（可选）
- ⚠️ `archived/` - 已废弃的代码和文档（可选上传，用于历史参考）

---

## ❌ 不应该上传的文件（已通过 .gitignore 忽略）

### 1. 敏感信息
- ❌ `.env` - **包含真实的 API keys，绝对不能上传！**
- ❌ `*.key`, `*.pem` - 密钥文件

### 2. Python 运行时文件
- ❌ `__pycache__/` - Python 字节码缓存
- ❌ `*.pyc`, `*.pyo` - 编译后的 Python 文件
- ❌ `.venv/`, `venv/`, `env/` - 虚拟环境目录
- ❌ `*.egg-info/` - 包元数据

### 3. 用户数据和持久化存储
- ❌ `data/` - **包含用户状态和 ChromaDB 数据**
  - `lamp_state.json` - 用户状态
  - `schedules.json` - 日程数据
  - `chroma_db_actions/` - 向量数据库文件
- ❌ `chroma_db/` - ChromaDB 数据库目录
- ❌ `*.db`, `*.sqlite`, `*.sqlite3` - 数据库文件

### 4. IDE 和编辑器配置
- ❌ `.vscode/` - VS Code 配置
- ❌ `.idea/` - PyCharm 配置
- ❌ `.cursor/` - Cursor IDE 配置

### 5. 测试和覆盖率报告
- ❌ `.pytest_cache/` - pytest 缓存
- ❌ `.coverage`, `htmlcov/` - 测试覆盖率报告

### 6. 日志和临时文件
- ❌ `*.log` - 日志文件
- ❌ `logs/` - 日志目录
- ❌ `tmp/`, `temp/` - 临时文件目录
- ❌ `*.bak`, `*.backup` - 备份文件

### 7. 操作系统文件
- ❌ `.DS_Store` - macOS 系统文件
- ❌ `Thumbs.db` - Windows 缩略图缓存

---

## 📋 上传前检查清单

在推送到 GitLab 之前，请确认：

- [ ] ✅ `.env` 文件**不在**仓库中（检查 `git status`）
- [ ] ✅ `data/` 目录**不在**仓库中
- [ ] ✅ `chroma_db/` 目录**不在**仓库中
- [ ] ✅ `.venv/` 或 `venv/` **不在**仓库中
- [ ] ✅ `__pycache__/` 目录**不在**仓库中
- [ ] ✅ `env-example.txt` **已上传**（作为配置模板）
- [ ] ✅ `requirements.txt` **已上传**（包含所有依赖）
- [ ] ✅ `README.md` **已上传**（包含项目说明和设置指南）

---

## 🚀 首次上传步骤

### 1. 检查当前状态
```bash
# 查看哪些文件会被提交
git status

# 查看 .gitignore 是否生效
git status --ignored
```

### 2. 初始化 Git 仓库（如果还没有）
```bash
git init
```

### 3. 添加远程仓库
```bash
git remote add origin <your-gitlab-repo-url>
```

### 4. 添加文件并提交
```bash
# 添加所有应该上传的文件
git add .

# 检查暂存区（确认没有敏感文件）
git status

# 提交
git commit -m "Initial commit: Project Animus V2"

# 推送到 GitLab
git push -u origin main
# 或
git push -u origin master
```

---

## ⚠️ 重要安全提示

1. **永远不要提交 `.env` 文件**
   - 如果意外提交了，需要：
     - 立即在 GitLab 上删除该文件
     - 重新生成所有 API keys
     - 使用 `git filter-branch` 或 `git filter-repo` 从历史中移除

2. **使用 `env-example.txt` 作为模板**
   - 新开发者可以复制此文件创建自己的 `.env`
   - 确保 `env-example.txt` 中所有值都是占位符

3. **定期检查 `.gitignore`**
   - 确保所有敏感文件类型都被忽略
   - 如果添加了新的数据目录，记得更新 `.gitignore`

---

## 📝 后续维护

### 添加新文件时的注意事项

1. **数据文件**：如果创建新的数据存储目录，记得添加到 `.gitignore`
2. **配置文件**：如果创建包含敏感信息的配置文件，使用 `.example` 后缀
3. **测试数据**：测试用的数据文件应该放在 `tests/fixtures/` 或使用 mock

### 更新依赖

```bash
# 更新 requirements.txt
pip freeze > requirements.txt

# 检查是否有新的依赖需要添加到 .gitignore
git status
```

---

## 🔗 相关文档

- [环境变量配置指南](./guides/README_DEMO.md)
- [API Key 配置说明](./API_KEY_RESTORED.md)
- [项目架构文档](./architecture/architecture_design.md)

---

**最后更新**: 2025-01-XX
**维护者**: Project Animus Team
