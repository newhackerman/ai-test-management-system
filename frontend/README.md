# AI测试管理系统 - 前端项目

## 项目简介

这是AI测试管理系统的前端项目，基于React + Antd + TypeScript开发，提供用户管理、角色管理和权限管理等功能。

## 技术栈

- React 18
- TypeScript
- Ant Design 5
- Redux Toolkit
- React Router 6
- Axios
- Craco
- Less

## 安装和运行

### Windows系统

1. 双击运行 `start.bat` 文件，或者手动执行以下命令：
   ```bash
   # 安装依赖
   npm install --legacy-peer-deps
   
   # 启动服务
   npm start
   ```

### Linux/macOS系统

1. 运行 `start.sh` 文件，或者手动执行以下命令：
   ```bash
   # 安装依赖
   npm install --legacy-peer-deps
   
   # 启动服务
   npm start
   ```

## 项目结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── api/             # API接口
│   ├── assets/          # 资源文件
│   ├── components/      # 公共组件
│   ├── config/          # 配置文件
│   ├── hooks/           # 自定义钩子
│   ├── layouts/         # 布局组件
│   ├── locales/         # 国际化
│   ├── pages/           # 页面组件
│   │   ├── auth/        # 认证相关页面
│   │   ├── user/        # 用户管理页面
│   │   ├── role/        # 角色管理页面
│   │   └── permission/  # 权限管理页面
│   ├── redux/           # Redux状态管理
│   │   ├── modules/     # 模块状态
│   │   └── store.ts     # Redux存储
│   ├── routes/          # 路由配置
│   ├── styles/          # 样式文件
│   ├── types/           # 类型定义
│   ├── utils/           # 工具函数
│   └── App.tsx          # 主应用组件
├── craco.config.js      # Craco配置
├── package.json         # 依赖包列表
├── start.bat            # Windows启动脚本
├── start.sh             # Linux/macOS启动脚本
└── README.md            # 说明文档
```

## 功能模块

### 认证模块
- 登录页面
- 注册页面
- 忘记密码页面

### 用户管理模块
- 用户列表页面
- 用户详情页面
- 用户创建/编辑页面
- 用户个人资料页面

### 角色管理模块
- 角色列表页面
- 角色创建/编辑页面

### 权限管理模块
- 权限列表页面
- 权限创建/编辑页面

## 开发指南

### 添加新页面

1. 在 `src/pages` 目录下创建新的页面组件
2. 在 `src/routes` 目录下添加路由配置
3. 在 `src/redux/modules` 目录下添加状态管理（如果需要）

### 添加新组件

1. 在 `src/components` 目录下创建新的组件
2. 在组件文件中导出组件
3. 在需要的页面中导入并使用组件

### 添加新API

1. 在 `src/api` 目录下创建新的API文件
2. 在API文件中定义接口函数
3. 在页面或Redux中导入并使用API函数

### 添加新样式

1. 在 `src/styles` 目录下创建新的样式文件
2. 在组件中导入样式文件
3. 使用Less语法编写样式

## 注意事项

1. 由于依赖冲突问题，安装依赖时需要使用 `--legacy-peer-deps` 参数
2. 开发时请确保后端服务已经启动，并运行在 http://localhost:8000
3. 修改API地址时，请同时修改 `package.json` 中的 proxy 配置