// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, Row, Steps, message } from 'antd';
import { MailOutlined, SafetyOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import authService from '@/services/authService';
import './ForgotPassword.less';

const ForgotPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [captchaInfo, setCaptchaInfo] = useState<{ key: string; image: string } | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');

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

  const handleSubmitEmail = async (values: any) => {
    try {
      setLoading(true);
      await authService.forgotPassword({
        email: values.email,
        captcha: values.captcha,
        captcha_key: values.captcha_key
      });
      setEmail(values.email);
      setCurrentStep(1);
      message.success('重置密码链接已发送到您的邮箱');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.response?.data?.message || error?.message || '发送重置密码链接失败');
      void fetchCaptcha();
      form.setFieldsValue({ captcha: '' });
    } finally {
      setLoading(false);
    }
  };

  const handleResendEmail = async () => {
    if (!email) return;
    try {
      setLoading(true);
      await authService.forgotPassword({
        email,
        captcha: form.getFieldValue('captcha'),
        captcha_key: form.getFieldValue('captcha_key')
      });
      message.success('重置密码链接已重新发送');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.response?.data?.message || error?.message || '重新发送失败');
      void fetchCaptcha();
    } finally {
      setLoading(false);
    }
  };

  const emailForm = (
    <Form form={form} name="forgot-password" onFinish={handleSubmitEmail} layout="vertical" size="large">
      <Form.Item
        name="email"
        label="邮箱"
        rules={[
          { required: true, message: '请输入邮箱' },
          { type: 'email', message: '请输入有效的邮箱地址' }
        ]}
      >
        <Input prefix={<MailOutlined />} placeholder="请输入注册邮箱" />
      </Form.Item>

      <Form.Item label="验证码">
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
          发送重置密码链接
        </Button>
      </Form.Item>

      <Form.Item className="forgot-password-form-login">
        已有账号？<Link to="/auth/login">立即登录</Link>
      </Form.Item>
    </Form>
  );

  const sentView = (
    <div className="email-sent-container">
      <div className="email-sent-icon">
        <MailOutlined />
      </div>
      <h3>重置密码链接已发送</h3>
      <p>
        我们已向 <strong>{email}</strong> 发送重置密码链接。
      </p>
      <p>请检查邮箱和垃圾邮件文件夹，并按邮件中的链接重置密码。</p>
      <div className="email-sent-actions">
        <Button type="primary" loading={loading} onClick={handleResendEmail}>
          重新发送邮件
        </Button>
        <Button onClick={() => navigate('/auth/login')}>返回登录</Button>
      </div>
    </div>
  );

  return (
    <div className="forgot-password-container">
      <Row justify="center" align="middle" style={{ minHeight: '100vh' }}>
        <Col xs={22} sm={18} md={14} lg={10} xl={8}>
          <Card className="forgot-password-card">
            <div className="forgot-password-header">
              <h1>忘记密码</h1>
              <p>请按步骤重置您的密码</p>
            </div>

            <Steps
              current={currentStep}
              className="forgot-password-steps"
              items={[
                { title: '验证邮箱' },
                { title: '检查邮箱' }
              ]}
            />

            <div className="steps-content">{currentStep === 0 ? emailForm : sentView}</div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ForgotPasswordPage;
