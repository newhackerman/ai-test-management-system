import { z } from 'zod'
import { VALIDATION, REGEX } from './constants'

// 基础验证规则
export const validators = {
  // 必填字段
  required: (message = '此字段为必填项') => z.string().min(1, message),
  
  // 邮箱验证
  email: (message = '请输入有效的邮箱地址') => 
    z.string().regex(VALIDATION.EMAIL.PATTERN, message),
  
  // 手机号验证
  phone: (message = '请输入有效的手机号') => 
    z.string().regex(VALIDATION.PHONE.PATTERN, message),
  
  // 密码验证
  password: (message = '密码不符合要求') => {
    let schema = z.string().min(VALIDATION.PASSWORD.MIN_LENGTH, 
      `密码长度至少${VALIDATION.PASSWORD.MIN_LENGTH}位`)
    
    if (VALIDATION.PASSWORD.REQUIRE_UPPERCASE) {
      schema = schema.regex(/[A-Z]/, '密码必须包含大写字母')
    }
    
    if (VALIDATION.PASSWORD.REQUIRE_LOWERCASE) {
      schema = schema.regex(/[a-z]/, '密码必须包含小写字母')
    }
    
    if (VALIDATION.PASSWORD.REQUIRE_NUMBERS) {
      schema = schema.regex(/\d/, '密码必须包含数字')
    }
    
    if (VALIDATION.PASSWORD.REQUIRE_SPECIAL_CHARS) {
      schema = schema.regex(/[!@#$%^&*(),.?":{}|<>]/, '密码必须包含特殊字符')
    }
    
    return schema.max(VALIDATION.PASSWORD.MAX_LENGTH, 
      `密码长度不能超过${VALIDATION.PASSWORD.MAX_LENGTH}位`)
  },
  
  // 用户名验证
  username: (message = '用户名格式不正确') => 
    z.string()
      .min(VALIDATION.USERNAME.MIN_LENGTH, `用户名长度至少${VALIDATION.USERNAME.MIN_LENGTH}位`)
      .max(VALIDATION.USERNAME.MAX_LENGTH, `用户名长度不能超过${VALIDATION.USERNAME.MAX_LENGTH}位`)
      .regex(VALIDATION.USERNAME.PATTERN, '用户名只能包含字母、数字、下划线和连字符'),
  
  // URL验证
  url: (message = '请输入有效的URL') => 
    z.string().regex(REGEX.URL, message),
  
  // IP地址验证
  ip: (message = '请输入有效的IP地址') => 
    z.string().regex(REGEX.IP, message),
  
  // UUID验证
  uuid: (message = '请输入有效的UUID') => 
    z.string().regex(REGEX.UUID, message),
  
  // 十六进制颜色验证
  hexColor: (message = '请输入有效的十六进制颜色') => 
    z.string().regex(REGEX.HEX_COLOR, message),
  
  // 数字范围验证
  numberRange: (min: number, max: number, message?: string) => 
    z.number().min(min, message || `数值不能小于${min}`)
      .max(max, message || `数值不能大于${max}`),
  
  // 字符串长度验证
  stringLength: (min: number, max: number, message?: string) => 
    z.string().min(min, message || `长度不能少于${min}个字符`)
      .max(max, message || `长度不能超过${max}个字符`),
  
  // 数组长度验证
  arrayLength: (min: number, max: number, message?: string) => 
    z.array(z.any()).min(min, message || `至少选择${min}项`)
      .max(max, message || `最多选择${max}项`),
  
  // 文件大小验证
  fileSize: (maxSize: number, message?: string) => 
    z.instanceof(File).refine(
      (file) => file.size <= maxSize,
      message || `文件大小不能超过${Math.round(maxSize / 1024 / 1024)}MB`
    ),
  
  // 文件类型验证
  fileType: (allowedTypes: string[], message?: string) => 
    z.instanceof(File).refine(
      (file) => allowedTypes.includes(file.type),
      message || `只允许上传${allowedTypes.join(', ')}格式的文件`
    ),
  
  // 日期范围验证
  dateRange: (startDate: Date, endDate: Date, message?: string) => 
    z.date().min(startDate, message || `日期不能早于${startDate.toLocaleDateString()}`)
      .max(endDate, message || `日期不能晚于${endDate.toLocaleDateString()}`),
  
  // 确认密码验证
  confirmPassword: (passwordField: string) => 
    z.string().min(1, '请确认密码'),
}

// 常用表单验证模式
export const schemas = {
  // 登录表单
  login: z.object({
    username: validators.required('请输入用户名'),
    password: validators.required('请输入密码'),
    remember: z.boolean().optional(),
  }),
  
  // 注册表单
  register: z.object({
    username: validators.username(),
    email: validators.email(),
    password: validators.password(),
    confirmPassword: validators.confirmPassword('password'),
    agree: z.boolean().refine(val => val === true, '请同意服务条款'),
  }).refine(data => data.password === data.confirmPassword, {
    message: '两次输入的密码不一致',
    path: ['confirmPassword'],
  }),
  
  // 修改密码表单
  changePassword: z.object({
    currentPassword: validators.required('请输入当前密码'),
    newPassword: validators.password(),
    confirmPassword: validators.confirmPassword('newPassword'),
  }).refine(data => data.newPassword === data.confirmPassword, {
    message: '两次输入的密码不一致',
    path: ['confirmPassword'],
  }),
  
  // 用户资料表单
  userProfile: z.object({
    firstName: validators.stringLength(1, 50, '姓名长度为1-50个字符').optional(),
    lastName: validators.stringLength(1, 50, '姓名长度为1-50个字符').optional(),
    email: validators.email(),
    phone: validators.phone().optional(),
    department: validators.stringLength(1, 100).optional(),
    position: validators.stringLength(1, 100).optional(),
  }),
  
  // 项目表单
  project: z.object({
    name: validators.stringLength(1, 100, '项目名称长度为1-100个字符'),
    description: validators.stringLength(0, 500, '项目描述不能超过500个字符').optional(),
    status: z.enum(['planning', 'active', 'on_hold', 'completed', 'archived']),
    startDate: z.date().optional(),
    endDate: z.date().optional(),
    members: z.array(z.string()).optional(),
  }).refine(data => {
    if (data.startDate && data.endDate) {
      return data.startDate <= data.endDate
    }
    return true
  }, {
    message: '结束日期不能早于开始日期',
    path: ['endDate'],
  }),
  
  // 测试用例表单
  testCase: z.object({
    name: validators.stringLength(1, 200, '测试用例名称长度为1-200个字符'),
    description: validators.stringLength(0, 1000, '描述不能超过1000个字符').optional(),
    projectId: validators.required('请选择项目'),
    priority: z.enum(['low', 'medium', 'high', 'critical']),
    tags: z.array(z.string()).optional(),
    steps: z.array(z.object({
      action: validators.stringLength(1, 500, '操作步骤不能为空'),
      expected: validators.stringLength(1, 500, '预期结果不能为空'),
    })).min(1, '至少添加一个测试步骤'),
  }),
  
  // 文件上传表单
  fileUpload: z.object({
    file: validators.fileSize(10 * 1024 * 1024) // 10MB
      .and(validators.fileType(['image/jpeg', 'image/png', 'application/pdf'])),
    description: validators.stringLength(0, 200).optional(),
  }),
  
  // 搜索表单
  search: z.object({
    query: validators.stringLength(0, 100).optional(),
    filters: z.record(z.any()).optional(),
    sortBy: z.string().optional(),
    sortOrder: z.enum(['asc', 'desc']).optional(),
  }),
  
  // 配置表单
  config: z.object({
    key: validators.stringLength(1, 100, '配置键不能为空'),
    value: z.any(),
    description: validators.stringLength(0, 200).optional(),
    category: validators.stringLength(1, 50, '配置分类不能为空'),
  }),
}

// 验证工具函数
export const validationUtils = {
  /**
   * 验证单个字段
   */
  validateField<T>(schema: z.ZodSchema<T>, value: unknown): {
    success: boolean
    data?: T
    error?: string
  } {
    try {
      const data = schema.parse(value)
      return { success: true, data }
    } catch (error) {
      if (error instanceof z.ZodError) {
        return { 
          success: false, 
          error: error.errors[0]?.message || '验证失败' 
        }
      }
      return { success: false, error: '验证失败' }
    }
  },
  
  /**
   * 验证表单数据
   */
  validateForm<T>(schema: z.ZodSchema<T>, data: unknown): {
    success: boolean
    data?: T
    errors?: Record<string, string>
  } {
    try {
      const validData = schema.parse(data)
      return { success: true, data: validData }
    } catch (error) {
      if (error instanceof z.ZodError) {
        const errors: Record<string, string> = {}
        error.errors.forEach(err => {
          const path = err.path.join('.')
          errors[path] = err.message
        })
        return { success: false, errors }
      }
      return { success: false, errors: { _form: '验证失败' } }
    }
  },
  
  /**
   * 异步验证
   */
  async validateAsync<T>(
    schema: z.ZodSchema<T>, 
    value: unknown
  ): Promise<{
    success: boolean
    data?: T
    error?: string
  }> {
    try {
      const data = await schema.parseAsync(value)
      return { success: true, data }
    } catch (error) {
      if (error instanceof z.ZodError) {
        return { 
          success: false, 
          error: error.errors[0]?.message || '验证失败' 
        }
      }
      return { success: false, error: '验证失败' }
    }
  },
  
  /**
   * 创建自定义验证器
   */
  createValidator<T>(
    validate: (value: T) => boolean | Promise<boolean>,
    message: string
  ) {
    return z.any().refine(validate, { message })
  },
  
  /**
   * 条件验证
   */
  conditionalValidation<T>(
    condition: (data: any) => boolean,
    schema: z.ZodSchema<T>,
    fallback?: z.ZodSchema<T>
  ) {
    return z.any().superRefine((data, ctx) => {
      if (condition(data)) {
        const result = schema.safeParse(data)
        if (!result.success) {
          result.error.errors.forEach(error => {
            ctx.addIssue(error)
          })
        }
      } else if (fallback) {
        const result = fallback.safeParse(data)
        if (!result.success) {
          result.error.errors.forEach(error => {
            ctx.addIssue(error)
          })
        }
      }
    })
  },
}

// 导出类型
export type LoginSchema = z.infer<typeof schemas.login>
export type RegisterSchema = z.infer<typeof schemas.register>
export type ChangePasswordSchema = z.infer<typeof schemas.changePassword>
export type UserProfileSchema = z.infer<typeof schemas.userProfile>
export type ProjectSchema = z.infer<typeof schemas.project>
export type TestCaseSchema = z.infer<typeof schemas.testCase>
export type FileUploadSchema = z.infer<typeof schemas.fileUpload>
export type SearchSchema = z.infer<typeof schemas.search>
export type ConfigSchema = z.infer<typeof schemas.config>