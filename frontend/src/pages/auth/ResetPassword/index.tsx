// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, Progress, Row, message } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import authService from '@/services/authService';
import './ResetPassword.less';

const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [token, setToken] = useState('');
  const [tokenValid, setTokenValid] = useState(true);

  useEffect(() => {
    const tokenParam = new URLSearchParams(location.search).get('token');
    if (tokenParam) {
      setToken(tokenParam);
    } else {
      setTokenValid(false);
      message.error('重置密码链接无效或已过期');
    }
  }, [location.search]);

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

  const handleResetPassword = async (values: any) => {
    try {
      setLoading(true);
      await authService.resetPassword({
        token,
        new_password: values.new_password,
        confirm_password: values.confirm_password
      });
      message.success('密码重置成功，请使用新密码登录');
      navigate('/auth/login');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.response?.data?.message || error?.message || '重置密码失败');
    } finally {
      setLoading(false);
    }
  };

  const validateConfirmPassword = (_: any, value: string) => {
    if (!value) return Promise.reject(new Error('请确认密码'));
    if (value !== form.getFieldValue('new_password')) return Promise.reject(new Error('两次输入的密码不一致'));
    return Promise.resolve();
  };

  if (!tokenValid) {
    return (
      <div className="reset-password-container">
        <Row justify="center" align="middle" style={{ minHeight: '100vh' }}>
          <Col xs={22} sm={18} md={14} lg={10} xl={8}>
            <Card className="reset-password-card">
              <div className="reset-password-error">
                <h3>链接无效或已过期</h3>
                <p>请重新申请密码重置链接。</p>
                <Button type="primary" onClick={() => navigate('/auth/forgot-password')}>
                  重新申请重置密码
                </Button>
              </div>
            </Card>
          </Col>
        </Row>
      </div>
    );
  }

  return (
    <div className="reset-password-container">
      <Row justify="center" align="middle" style={{ minHeight: '100vh' }}>
        <Col xs={22} sm={18} md={14} lg={10} xl={8}>
          <Card className="reset-password-card">
            <div className="reset-password-header">
              <h1>重置密码</h1>
              <p>请输入您的新密码</p>
            </div>

            <Form form={form} name="reset-password" onFinish={handleResetPassword} scrollToFirstError size="large" layout="vertical">
              <Form.Item
                name="new_password"
                label="新密码"
                rules={[
                  { required: true, message: '请输入新密码' },
                  { min: 8, message: '密码至少 8 个字符' }
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="请输入新密码" onChange={(event) => calculatePasswordStrength(event.target.value)} />
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
                label="确认密码"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: '请确认密码' },
                  { validator: validateConfirmPassword }
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="请再次输入新密码" />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block>
                  重置密码
                </Button>
              </Form.Item>

              <Form.Item className="reset-password-form-login">
                已有账号？<Link to="/auth/login">立即登录</Link>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ResetPasswordPage;
