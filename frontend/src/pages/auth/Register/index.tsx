// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, Progress, Row, message } from 'antd';
import { LockOutlined, MailOutlined, SafetyOutlined, UserOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useAppDispatch } from '@/store/hooks';
import { registerFailure, registerRequest, registerSuccess } from '@/store/reducers/authSlice';
import authService from '@/services/authService';
import './Register.less';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [form] = Form.useForm();
  const [captchaInfo, setCaptchaInfo] = useState<{ key: string; image: string } | null>(null);
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchCaptcha = async () => {
    try {
      const captcha = await authService.getCaptcha();
      setCaptchaInfo(captcha);
      form.setFieldsValue({ captcha_key: captcha.key });
    } catch {
      setCaptchaInfo(null);
    }
  };

  useEffect(() => {
    void fetchCaptcha();
  }, []);

  const calculatePasswordStrength = (password: string) => {
    let strength = 0;
    if (password.length >= 8) strength += 30;
    if (password.length >= 12) strength += 10;
    if (/\d/.test(password)) strength += 15;
    if (/[a-z]/.test(password)) strength += 15;
    if (/[A-Z]/.test(password)) strength += 15;
    if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) strength += 15;
    setPasswordStrength(Math.min(strength, 100));
  };

  const getPasswordStrengthColor = () => {
    if (passwordStrength < 40) return '#ff4d4f';
    if (passwordStrength < 70) return '#faad14';
    return '#52c41a';
  };

  const getPasswordStrengthText = () => {
    if (passwordStrength < 40) return '弱';
    if (passwordStrength < 70) return '中';
    if (passwordStrength < 90) return '强';
    return '非常强';
  };

  const handleRegister = async (values: any) => {
    try {
      setLoading(true);
      dispatch(registerRequest(values));
      await authService.register({
        username: values.username,
        email: values.email,
        password: values.password,
        confirm_password: values.confirm_password,
        captcha: values.captcha,
        captcha_key: values.captcha_key
      });

      dispatch(registerSuccess());
      message.success('注册成功，请登录您的账户');
      navigate('/auth/login');
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '注册失败';
      dispatch(registerFailure(errorMessage));
      message.error(errorMessage);
      void fetchCaptcha();
      form.setFieldsValue({ captcha: '' });
    } finally {
      setLoading(false);
    }
  };

  const validateConfirmPassword = (_: any, value: string) => {
    if (!value) return Promise.reject(new Error('请确认密码'));
    if (value !== form.getFieldValue('password')) return Promise.reject(new Error('两次输入的密码不一致'));
    return Promise.resolve();
  };

  return (
    <div className="register-container">
      <Row justify="center" align="middle" style={{ minHeight: '100vh' }}>
        <Col xs={22} sm={18} md={14} lg={10} xl={8}>
          <Card className="register-card">
            <div className="register-header">
              <h1>创建账户</h1>
              <p>请填写以下信息完成注册</p>
            </div>

            <Form form={form} name="register" onFinish={handleRegister} scrollToFirstError size="large">
              <Form.Item
                name="username"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { min: 3, message: '用户名至少 3 个字符' },
                  { max: 20, message: '用户名最多 20 个字符' },
                  { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' }
                ]}
              >
                <Input prefix={<UserOutlined />} placeholder="用户名" />
              </Form.Item>

              <Form.Item
                name="email"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入有效的邮箱地址' }
                ]}
              >
                <Input prefix={<MailOutlined />} placeholder="邮箱" />
              </Form.Item>

              <Form.Item
                name="password"
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: 8, message: '密码至少 8 个字符' }
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="密码" onChange={(event) => calculatePasswordStrength(event.target.value)} />
              </Form.Item>

              {passwordStrength > 0 && (
                <div className="password-strength">
                  <div className="strength-label">密码强度：</div>
                  <Progress percent={passwordStrength} strokeColor={getPasswordStrengthColor()} showInfo={false} />
                  <div className="strength-text" style={{ color: getPasswordStrengthColor() }}>
                    {getPasswordStrengthText()}
                  </div>
                </div>
              )}

              <Form.Item
                name="confirm_password"
                dependencies={['password']}
                rules={[
                  { required: true, message: '请确认密码' },
                  { validator: validateConfirmPassword }
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="确认密码" />
              </Form.Item>

              <Form.Item>
                <Row gutter={8}>
                  <Col span={16}>
                    <Form.Item name="captcha" noStyle>
                      <Input prefix={<SafetyOutlined />} placeholder="验证码" />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    {captchaInfo ? (
                      <button type="button" className="captcha-image" onClick={fetchCaptcha} dangerouslySetInnerHTML={{ __html: captchaInfo.image }} />
                    ) : (
                      <Button onClick={fetchCaptcha} block>
                        获取验证码
                      </Button>
                    )}
                  </Col>
                </Row>
                <Form.Item name="captcha_key" hidden>
                  <Input />
                </Form.Item>
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block>
                  注册
                </Button>
              </Form.Item>

              <Form.Item className="register-form-login">
                已有账号？<Link to="/auth/login">立即登录</Link>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default RegisterPage;
