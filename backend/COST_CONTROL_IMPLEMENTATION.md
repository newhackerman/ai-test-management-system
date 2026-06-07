# AI助手成本控制机制实现文档

## 概述

本文档描述了AI助手模块中成本控制机制的完整实现，包括预算管理、配额控制、使用监控和告警系统。

## 实现的功能

### 1. 成本控制服务 (CostControlService)

#### 核心功能
- **预算管理**: 支持日/周/月/年预算控制
- **配额管理**: Token和请求数量限制
- **使用监控**: 实时使用情况跟踪
- **告警系统**: 多级别告警机制
- **成本分析**: 详细的成本分解和统计

#### 预算配置类型
```python
class CostBudget:
    budget_id: str              # 预算ID
    name: str                   # 预算名称
    period: BudgetPeriod        # 预算周期 (daily/weekly/monthly/yearly)
    amount: Decimal             # 预算金额
    currency: str               # 货币类型
    providers: List[str]        # 适用的AI提供商
    users: List[int]            # 适用的用户
    departments: List[str]      # 适用的部门
    warning_threshold: float    # 告警阈值 (默认80%)
    critical_threshold: float   # 严重告警阈值 (默认90%)
    auto_disable_on_exceed: bool # 超预算时自动禁用
    allow_overage: bool         # 是否允许超支
    overage_limit: float        # 允许超支比例
```

#### 配额配置类型
```python
class UsageQuota:
    quota_id: str               # 配额ID
    name: str                   # 配额名称
    period: BudgetPeriod        # 配额周期
    token_limit: int            # Token限制
    request_limit: int          # 请求数限制
    providers: List[str]        # 适用的AI提供商
    users: List[int]            # 适用的用户
    departments: List[str]      # 适用的部门
    auto_reset: bool            # 自动重置
    grace_period_minutes: int   # 宽限期
```

### 2. AI路由服务集成

#### 成本控制检查
在AI请求路由过程中，系统会自动执行以下检查：

1. **预算限制检查**
   - 系统级预算检查
   - 用户级预算检查
   - 提供商级预算检查

2. **配额限制检查**
   - Token配额检查
   - 请求数配额检查
   - 用户级配额检查

3. **智能降级策略**
   - 当首选提供商超限时，自动选择成本更低的替代方案
   - 保持服务可用性的同时控制成本

#### 成本估算增强
```python
async def _estimate_cost(self, provider: AIProvider, request: AIRequest) -> float:
    # 分别计算输入和输出Token成本
    input_cost = input_tokens * cost_per_input_token
    output_cost = output_tokens * cost_per_output_token
    request_cost = cost_per_request
    
    # 根据任务复杂度调整
    complexity_factor = self._get_complexity_cost_factor(request)
    total_cost = (input_cost + output_cost + request_cost) * complexity_factor
    
    return total_cost
```

### 3. 实际使用记录

#### 使用情况跟踪
```python
async def record_actual_usage(self, provider: AIProvider, user_id: int,
                             input_tokens: int, output_tokens: int,
                             actual_cost: float, response_time: float,
                             success: bool = True) -> None:
    # 记录到成本控制服务
    await self.cost_control.record_usage(...)
    
    # 更新提供商健康状态
    await self._update_provider_health(...)
```

### 4. 成本控制API

#### 主要端点
- `GET /api/v1/cost-control/summary` - 获取成本摘要
- `GET /api/v1/cost-control/alerts` - 获取成本告警
- `POST /api/v1/cost-control/budgets` - 创建预算配置
- `POST /api/v1/cost-control/quotas` - 创建配额配置
- `POST /api/v1/cost-control/check` - 检查成本和配额限制
- `POST /api/v1/cost-control/usage` - 记录使用情况

#### 权限控制
- 普通用户只能查看和操作自己的数据
- 管理员可以查看和管理所有用户的数据
- 预算和配额配置需要管理员权限

### 5. 告警系统

#### 告警级别
```python
class AlertLevel(Enum):
    INFO = "info"           # 信息级别
    WARNING = "warning"     # 警告级别
    CRITICAL = "critical"   # 严重级别
    EMERGENCY = "emergency" # 紧急级别
```

#### 告警触发条件
- 预算使用率达到警告阈值 (默认80%)
- 预算使用率达到严重阈值 (默认90%)
- 配额使用率接近限制
- 系统级资源超限

### 6. 默认配置

#### 系统级预算
- 月度预算: $1000
- 日预算: $50 (允许20%超支)

#### 用户级预算
- 日预算: $5 (严格限制)

#### 系统级配额
- 日Token配额: 100万
- 日请求配额: 1万

#### 用户级配额
- 普通用户日Token配额: 5万
- 普通用户日请求配额: 500
- 高级用户日Token配额: 20万
- 高级用户日请求配额: 2000

## 数据库模型扩展

### AIModelConfig 扩展
```sql
-- 成本配置字段
cost_per_input_token FLOAT,     -- 输入Token成本
cost_per_output_token FLOAT,    -- 输出Token成本
cost_per_request FLOAT,         -- 每请求成本

-- 配额限制字段
daily_quota INTEGER,            -- 每日配额
monthly_quota INTEGER,          -- 每月配额
user_daily_quota INTEGER,       -- 用户每日配额
concurrent_limit INTEGER        -- 并发限制
```

### AIUsageStats 使用统计
```sql
-- 基本统计
request_count INTEGER,          -- 请求次数
success_count INTEGER,          -- 成功次数
error_count INTEGER,            -- 错误次数

-- Token统计
input_tokens INTEGER,           -- 输入Token数
output_tokens INTEGER,          -- 输出Token数
total_tokens INTEGER,           -- 总Token数

-- 成本统计
total_cost FLOAT,               -- 总成本

-- 性能统计
avg_response_time FLOAT,        -- 平均响应时间
min_response_time FLOAT,        -- 最小响应时间
max_response_time FLOAT         -- 最大响应时间
```

## 使用示例

### 1. 检查成本限制
```python
# 检查预算和配额限制
cost_check = await cost_control.check_budget_limits(
    provider="openai", 
    user_id=1, 
    estimated_cost=Decimal("0.50")
)

quota_check = await cost_control.check_usage_quotas(
    provider="openai", 
    user_id=1, 
    estimated_tokens=1000
)

if cost_check[0] and quota_check[0]:
    # 允许请求
    proceed_with_request()
else:
    # 拒绝请求，返回告警信息
    return_error_with_alerts(cost_check[1] + quota_check[1])
```

### 2. 记录使用情况
```python
# 记录实际使用情况
await cost_control.record_usage(
    provider="openai",
    user_id=1,
    input_tokens=500,
    output_tokens=1000,
    cost=Decimal("0.10"),
    response_time=2.5,
    success=True
)
```

### 3. 获取成本摘要
```python
# 获取日成本摘要
summary = await cost_control.get_cost_summary(
    period=BudgetPeriod.DAILY,
    user_id=1
)

print(f"今日成本: ${summary['summary']['total_cost']}")
print(f"今日Token: {summary['summary']['total_tokens']}")
print(f"预算使用率: {summary['budgets']['user_daily']['percentage']:.1%}")
```

### 4. 创建自定义预算
```python
# 创建部门预算
department_budget = CostBudget(
    budget_id="engineering_monthly",
    name="工程部月度预算",
    period=BudgetPeriod.MONTHLY,
    amount=Decimal("500.00"),
    departments=["engineering"],
    warning_threshold=0.75,
    critical_threshold=0.90,
    auto_disable_on_exceed=False,
    allow_overage=True,
    overage_limit=0.15
)

cost_control.add_budget(department_budget)
```

## 监控和告警

### 1. 实时监控
- 成本使用情况实时跟踪
- 配额使用情况监控
- 提供商性能监控
- 用户使用行为分析

### 2. 告警机制
- 预算超限告警
- 配额接近告警
- 异常使用模式告警
- 系统性能告警

### 3. 报表功能
- 日/周/月成本报表
- 用户使用统计报表
- 提供商成本分析报表
- 趋势分析报表

## 性能优化

### 1. 缓存策略
- 使用情况缓存 (5分钟TTL)
- 预算状态缓存
- 配额状态缓存

### 2. 批量处理
- 批量使用记录更新
- 批量告警处理
- 批量统计计算

### 3. 异步处理
- 异步使用记录
- 异步告警发送
- 异步统计更新

## 安全考虑

### 1. 权限控制
- 基于角色的访问控制
- 用户数据隔离
- 管理员权限验证

### 2. 数据保护
- 成本数据加密存储
- 敏感信息脱敏
- 审计日志记录

### 3. 防滥用机制
- 请求频率限制
- 异常检测
- 自动封禁机制

## 测试覆盖

### 1. 单元测试
- 成本控制服务测试
- 预算检查测试
- 配额检查测试
- 使用记录测试

### 2. 集成测试
- AI路由服务集成测试
- 成本控制API测试
- 端到端流程测试

### 3. 性能测试
- 高并发场景测试
- 大数据量处理测试
- 响应时间测试

## 部署配置

### 1. 环境变量
```bash
# 成本控制配置
COST_CONTROL_ENABLED=true
DEFAULT_DAILY_BUDGET=50.00
DEFAULT_USER_DAILY_BUDGET=5.00
BUDGET_WARNING_THRESHOLD=0.8
BUDGET_CRITICAL_THRESHOLD=0.9

# 配额配置
DEFAULT_DAILY_TOKEN_QUOTA=1000000
DEFAULT_USER_DAILY_TOKEN_QUOTA=50000
DEFAULT_DAILY_REQUEST_QUOTA=10000
DEFAULT_USER_DAILY_REQUEST_QUOTA=500
```

### 2. 数据库迁移
```bash
# 运行数据库迁移
python manage.py migrate

# 初始化默认配置
python scripts/init_cost_control.py
```

## 总结

成本控制机制的实现提供了以下核心价值：

1. **成本可控**: 通过多层级预算和配额控制，确保AI服务成本在可控范围内
2. **智能路由**: 在成本控制约束下，智能选择最优的AI服务提供商
3. **实时监控**: 提供实时的成本和使用情况监控
4. **灵活配置**: 支持灵活的预算和配额配置，适应不同业务需求
5. **告警机制**: 及时发现和处理成本异常情况
6. **数据分析**: 提供详细的成本分析和使用统计

该实现确保了AI助手服务在提供高质量服务的同时，有效控制运营成本，为企业级应用提供了可靠的成本管理基础。