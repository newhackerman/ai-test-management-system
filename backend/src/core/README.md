# 依赖注入框架使用指南

## 概述

本项目实现了一个完整的依赖注入框架，支持服务注册、解析、生命周期管理等功能。框架与FastAPI深度集成，提供了便捷的依赖注入装饰器和中间件。

## 核心组件

### 1. ServiceContainer (服务容器)

服务容器是依赖注入框架的核心，负责管理服务的注册和解析。

```python
from src.core.container import ServiceContainer, ServiceLifetime

container = ServiceContainer()

# 注册瞬态服务
container.register_transient(MyService)

# 注册单例服务
container.register_singleton(MyService, MyServiceImpl)

# 注册作用域服务
container.register_scoped(MyService)

# 注册工厂函数
container.register_factory(MyService, create_my_service, ServiceLifetime.SINGLETON)

# 注册实例
container.register_instance(MyService, my_service_instance)
```

### 2. ServiceRegistry (服务注册表)

服务注册表提供了统一的服务注册和配置管理功能。

```python
from src.core.service_registry import ServiceRegistry, configure_services

# 配置所有服务
registry = configure_services()

# 初始化服务
await registry.initialize_services()

# 健康检查
health_status = await registry.health_check_services()
```

### 3. FastAPI集成

框架提供了与FastAPI的深度集成，包括中间件、装饰器和依赖函数。

```python
from fastapi import FastAPI
from src.core.fastapi_integration import setup_dependency_injection, Inject

app = FastAPI()

# 设置依赖注入
setup_dependency_injection(app)

# 在路由中使用依赖注入
@app.get("/api/test")
async def test_endpoint(
    ai_service: AIAssistantService = Inject(AIAssistantService)
):
    return await ai_service.process_query(...)
```

## 服务生命周期

框架支持三种服务生命周期：

### 1. Transient (瞬态)
每次请求都创建新的实例。

```python
container.register_transient(MyService)
```

### 2. Singleton (单例)
整个应用生命周期内只创建一次实例。

```python
container.register_singleton(MyService)
```

### 3. Scoped (作用域)
在特定作用域内保持单例，通常用于HTTP请求作用域。

```python
container.register_scoped(MyService)
```

## 使用方式

### 1. 基本服务注册

```python
# 简单服务
class MyService:
    def __init__(self):
        self.name = "MyService"

# 注册服务
container.register_singleton(MyService)

# 解析服务
service = container.get_service(MyService)
```

### 2. 依赖注入

```python
# 带依赖的服务
class DependentService:
    def __init__(self, my_service: MyService):
        self.my_service = my_service

# 注册服务（容器会自动解析依赖）
container.register_transient(DependentService)

# 解析服务（自动注入依赖）
service = container.get_service(DependentService)
```

### 3. 工厂函数

```python
def create_complex_service(my_service: MyService) -> ComplexService:
    service = ComplexService()
    service.configure(my_service)
    return service

container.register_factory(ComplexService, create_complex_service)
```

### 4. FastAPI路由中使用

```python
from src.core.fastapi_integration import Inject, with_services

# 方式1：使用Inject装饰器
@app.get("/api/service1")
async def endpoint1(service: MyService = Inject(MyService)):
    return service.get_data()

# 方式2：使用with_services装饰器
@app.get("/api/service2")
@with_services(MyService, AnotherService)
async def endpoint2(services: dict):
    my_service = services[MyService]
    another_service = services[AnotherService]
    return {"data": my_service.get_data()}

# 方式3：使用ServiceProvider
from src.core.fastapi_integration import ServiceProviderDep

@app.get("/api/service3")
async def endpoint3(provider: ServiceProvider = ServiceProviderDep):
    service = await provider.get_service(MyService)
    return service.get_data()
```

## 高级功能

### 1. 服务拦截器

```python
def logging_interceptor(instance):
    # 添加日志功能
    original_method = instance.some_method
    def logged_method(*args, **kwargs):
        logger.info(f"Calling {instance.__class__.__name__}.some_method")
        return original_method(*args, **kwargs)
    instance.some_method = logged_method
    return instance

container.add_interceptor(MyService, logging_interceptor)
```

### 2. 作用域管理

```python
# 创建自定义作用域
async with container.create_scope("custom_scope"):
    service = await container.get_service_async(ScopedService)
    # 在此作用域内，ScopedService保持单例
```

### 3. 服务验证

```python
# 验证所有服务注册
errors = container.validate_registrations()
if errors:
    for error in errors:
        print(f"Validation error: {error}")
```

## 配置示例

### 完整的应用配置

```python
from fastapi import FastAPI
from src.core.service_registry import configure_services, initialize_application_services
from src.core.fastapi_integration import setup_dependency_injection

async def create_app():
    app = FastAPI()
    
    # 配置依赖注入服务
    configure_services()
    
    # 设置FastAPI集成
    setup_dependency_injection(app)
    
    # 初始化服务
    await initialize_application_services()
    
    return app
```

### 自定义服务注册

```python
from src.core.service_registry import get_service_registry

registry = get_service_registry()

# 注册自定义服务
registry.container.register_singleton(MyCustomService)

# 添加服务配置
registry._service_configs[MyCustomService] = {
    'dependencies': [SomeDependency],
    'initialization_order': 5,
    'health_check_enabled': True
}
```

## 最佳实践

### 1. 服务设计

- 使用接口和抽象类定义服务契约
- 保持服务的单一职责
- 避免循环依赖
- 使用工厂函数处理复杂的初始化逻辑

### 2. 生命周期选择

- 无状态服务使用Singleton
- 有状态但需要隔离的服务使用Scoped
- 轻量级或需要每次创建的服务使用Transient

### 3. 错误处理

```python
from src.core.container import ServiceResolutionError

try:
    service = container.get_service(MyService)
except ServiceResolutionError as e:
    logger.error(f"Failed to resolve service: {e}")
    # 处理错误
```

### 4. 测试

```python
# 在测试中使用独立的容器
def test_my_service():
    test_container = ServiceContainer()
    test_container.register_transient(MyService)
    
    service = test_container.get_service(MyService)
    assert service is not None
```

## 健康检查

框架提供了内置的健康检查功能：

```python
# 访问 /health/di 端点查看依赖注入状态
{
    "status": "ok",
    "dependency_injection": {
        "status": "healthy",
        "container": {
            "registered_services_count": 6,
            "registered_services": ["ServiceContainer", "AIAssistantService", ...],
            "container_type": "ServiceContainer"
        },
        "services": {
            "status": "healthy",
            "services": {
                "ai_assistant": true,
                "ai_router": true,
                "conversation": true
            },
            "total_services": 3,
            "healthy_services": 3,
            "unhealthy_services": 0
        }
    }
}
```

## 故障排除

### 常见问题

1. **ServiceResolutionError**: 服务未注册或依赖无法解析
   - 检查服务是否已注册
   - 检查依赖关系是否正确
   - 使用`validate_registrations()`验证配置

2. **CircularDependencyError**: 循环依赖
   - 重新设计服务架构
   - 使用工厂函数或延迟初始化

3. **No active scope for scoped service**: 作用域服务在错误的上下文中使用
   - 确保在正确的作用域内使用
   - 考虑改用Singleton或Transient生命周期

### 调试技巧

```python
# 查看已注册的服务
services = container.get_registered_services()
print(f"Registered services: {[s.__name__ for s in services]}")

# 查看服务信息
from src.core.service_registry import get_service_registry
registry = get_service_registry()
info = registry.get_all_services_info()
print(json.dumps(info, indent=2))
```

## 扩展

框架设计为可扩展的，你可以：

1. 实现自定义的服务生命周期
2. 添加新的拦截器类型
3. 扩展健康检查功能
4. 集成其他框架（如Celery、SQLAlchemy等）

通过这个依赖注入框架，你可以构建松耦合、可测试、可维护的应用程序。