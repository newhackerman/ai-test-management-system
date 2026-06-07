import { z } from 'zod'
import { useForm, type FieldValues, type Path, type UseFormProps, type UseFormReturn } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'

export const validationRules = {
  required: (message = '此字段为必填项') => z.string().min(1, message),
  email: (message = '请输入有效的邮箱地址') => z.string().email(message),
  password: (message = '密码至少需要 8 个字符') => z.string().min(8, message),
  phone: (message = '请输入有效的手机号') => z.string().regex(/^1[3-9]\d{9}$/, message),
  url: (message = '请输入有效的 URL') => z.string().url(message),
  number: (message = '请输入有效的数字') => z.number({ message }),
  positiveNumber: (message = '请输入正数') => z.number().positive(message),
  integer: (message = '请输入整数') => z.number().int(message),
  minLength: (min: number, message?: string) => z.string().min(min, message || `至少需要 ${min} 个字符`),
  maxLength: (max: number, message?: string) => z.string().max(max, message || `最多 ${max} 个字符`),
  minValue: (min: number, message?: string) => z.number().min(min, message || `最小值为 ${min}`),
  maxValue: (max: number, message?: string) => z.number().max(max, message || `最大值为 ${max}`),
  regex: (pattern: RegExp, message = '格式不正确') => z.string().regex(pattern, message),
  oneOf: <T extends readonly [string, ...string[]]>(values: T, message = '请选择有效选项') =>
    z.enum(values, { message }),
  array: (schema: z.ZodTypeAny, message = '请至少选择一项') => z.array(schema).min(1, message),
  file: (message = '请选择文件') => z.instanceof(File, { message }),
  fileSize: (maxSize: number, message?: string) =>
    z.instanceof(File).refine((file) => file.size <= maxSize, message || `文件大小不能超过 ${Math.round(maxSize / 1024 / 1024)}MB`),
  fileType: (types: string[], message?: string) =>
    z.instanceof(File).refine((file) => types.includes(file.type), message || `文件类型必须是 ${types.join(', ')}`),
}

export const commonSchemas = {
  login: z.object({
    username: validationRules.required('请输入用户名'),
    password: validationRules.required('请输入密码'),
    rememberMe: z.boolean().optional(),
  }),
  register: z.object({
    username: validationRules.required('请输入用户名').pipe(validationRules.minLength(3, '用户名至少 3 个字符')),
    email: validationRules.email(),
    password: validationRules.password(),
    confirmPassword: validationRules.required('请确认密码'),
  }).refine((data) => data.password === data.confirmPassword, {
    message: '两次输入的密码不一致',
    path: ['confirmPassword'],
  }),
  profile: z.object({
    firstName: z.string().optional(),
    lastName: z.string().optional(),
    email: validationRules.email(),
    phone: validationRules.phone().optional(),
    bio: z.string().max(500, '简介最多 500 个字符').optional(),
  }),
  changePassword: z.object({
    currentPassword: validationRules.required('请输入当前密码'),
    newPassword: validationRules.password(),
    confirmPassword: validationRules.required('请确认新密码'),
  }).refine((data) => data.newPassword === data.confirmPassword, {
    message: '两次输入的新密码不一致',
    path: ['confirmPassword'],
  }),
  project: z.object({
    name: validationRules.required('请输入项目名称').pipe(validationRules.minLength(2, '项目名称至少 2 个字符')),
    description: z.string().max(1000, '描述最多 1000 个字符').optional(),
    status: validationRules.oneOf(['active', 'inactive', 'archived'], '请选择项目状态'),
  }),
  testCase: z.object({
    name: validationRules.required('请输入测试用例名称'),
    description: z.string().max(2000, '描述最多 2000 个字符').optional(),
    priority: validationRules.oneOf(['low', 'medium', 'high', 'critical'], '请选择优先级'),
    tags: z.array(z.string()).optional(),
    steps: z.array(z.object({
      action: validationRules.required('请输入操作步骤'),
      expected: validationRules.required('请输入预期结果'),
    })).min(1, '至少需要一个测试步骤'),
  }),
}

export function useZodForm<TSchema extends z.ZodTypeAny>(
  schema: TSchema,
  options?: Omit<UseFormProps<z.infer<TSchema>>, 'resolver'>,
): UseFormReturn<z.infer<TSchema>> {
  return useForm<z.infer<TSchema>>({
    resolver: zodResolver(schema),
    ...options,
  })
}

export function getFieldError<T extends FieldValues>(errors: any, name: Path<T>): string | undefined {
  return errors?.[name]?.message
}

export const formTransforms = {
  emptyStringToUndefined: (value: string) => (value === '' ? undefined : value),
  stringToNumber: (value: string) => (value === '' ? undefined : Number(value)),
  stringToBoolean: (value: string | boolean) => value === true || value === 'true',
  stringToArray: (value: string) => (value ? value.split(',').map((item) => item.trim()).filter(Boolean) : []),
  fileListToArray: (fileList: FileList | null) => (fileList ? Array.from(fileList) : []),
}

export class FormSubmissionHandler<T extends FieldValues> {
  constructor(
    private form: UseFormReturn<T>,
    private onSubmit: (data: T) => Promise<void> | void,
    private onError?: (error: unknown) => void,
  ) {}

  handleSubmit = async (data: T) => {
    try {
      await this.onSubmit(data)
    } catch (error) {
      this.onError?.(error)
    }
  }

  getSubmitHandler = () => this.form.handleSubmit(this.handleSubmit)
  reset = (values?: Partial<T>) => this.form.reset(values as any)
  setFieldError = (field: Path<T>, message: string) => this.form.setError(field, { message })
  setFieldErrors = (errors: Record<string, string>) => {
    Object.entries(errors).forEach(([field, message]) => this.setFieldError(field as Path<T>, message))
  }
  clearFieldError = (field: Path<T>) => this.form.clearErrors(field)
  clearAllErrors = () => this.form.clearErrors()
}

export const formUtils = {
  conditionalValidation: <T,>(condition: (data: T) => boolean, schema: z.ZodTypeAny) =>
    z.any().superRefine((data, context) => {
      if (!condition(data)) return
      const result = schema.safeParse(data)
      if (!result.success) {
        result.error.issues.forEach((issue) => context.addIssue(issue))
      }
    }),
  asyncValidation: <T,>(validator: (value: T) => Promise<boolean>, message: string) =>
    z.any().refine(validator, { message }),
  customValidation: <T,>(validator: (value: T) => boolean, message: string) =>
    z.any().refine(validator, { message }),
  mergeSchemas: <T extends z.ZodRawShape, U extends z.ZodRawShape>(schema1: z.ZodObject<T>, schema2: z.ZodObject<U>) =>
    schema1.merge(schema2),
  extendSchema: <T extends z.ZodRawShape, U extends z.ZodRawShape>(baseSchema: z.ZodObject<T>, extension: U) =>
    baseSchema.extend(extension),
}

export type FormSchema<T extends z.ZodTypeAny> = z.infer<T>
export type ValidationRule<T = any> = z.ZodType<T>

export default {
  validationRules,
  commonSchemas,
  useZodForm,
  getFieldError,
  formTransforms,
  FormSubmissionHandler,
  formUtils,
}
