// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { Button, Card, Checkbox, Col, Form, Input, Row, Tabs, message } from 'antd';
import { LockOutlined, MobileOutlined, SafetyOutlined, UserOutlined } from '@ant-design/icons';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAppDispatch } from '@/store/hooks';
import { loginFailure, loginRequest, loginSuccess } from '@/store/reducers/authSlice';
import authService from '@/services/authService';
import './Login.less';

type LoginType = 'account' | 'mobile';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const [form] = Form.useForm();
  const [mobileForm] = Form.useForm();
  const [captchaInfo, setCaptchaInfo] = useState<{ key: string; image: string } | null>(null);
  const [loginType, setLoginType] = useState<LoginType>('account');
  const [loading, setLoading] = useState(false);

  const from = (location.state as any)?.from?.pathname || (location.state as any)?.from || '/';

  const fetchCaptcha = async () => {
    try {
      const captcha = await authService.getCaptcha();
      setCaptchaInfo(captcha);
      form.setFieldsValue({ captcha_key: captcha.key });
      mobileForm.setFieldsValue({ captcha_key: captcha.key });
    } catch (error) {
      setCaptchaInfo(null);
    }
  };

  useEffect(() => {
    void fetchCaptcha();
  }, []);

  const submitLogin = async (values: any, mode: LoginType) => {
    try {
      setLoading(true);
      dispatch(loginRequest(values));

      const response = await authService.login({
        username: mode === 'mobile' ? values.mobile : values.username,
        password: mode === 'mobile' ? values.sms_code : values.password,
        captcha: values.captcha,
        captcha_key: values.captcha_key
      });

      dispatch(
        loginSuccess({
          token: response.access_token,
          refreshToken: response.refresh_token,
          user: response.user
        })
      );

      message.success('登录成功');
      navigate(from, { replace: true });
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '登录失败';
      dispatch(loginFailure(errorMessage));
      message.error(errorMessage);
      void fetchCaptcha();
      form.setFieldsValue({ captcha: '' });
      mobileForm.setFieldsValue({ captcha: '' });
    } finally {
      setLoading(false);
    }
  };

  const handleSendSmsCode = () => {
    message.info('短信验证码功能需要后端短信服务接入后启用');
  };

  const renderCaptcha = () => (
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
      <Form.Item name="captcha_key" hidden>
        <Input />
      </Form.Item>
    </Row>
  );

  return (
    <div className="login-container">
      <Row justify="center" align="middle" style={{ minHeight: '100vh' }}>
        <Col xs={22} sm={18} md={12} lg={8} xl={6}>
          <Card className="login-card">
            <div className="login-header">
              <h1>AI 测试管理系统</h1>
              <p>欢迎回来，请登录您的账户</p>
            </div>

            <Tabs
              activeKey={loginType}
              onChange={(key) => setLoginType(key as LoginType)}
              items={[
                {
                  key: 'account',
                  label: '账号密码登录',
                  children: (
                    <Form form={form} name="login" initialValues={{ remember: true }} onFinish={(values) => submitLogin(values, 'account')} size="large">
                      <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                        <Input prefix={<UserOutlined />} placeholder="用户名" />
                      </Form.Item>

                      <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                        <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                      </Form.Item>

                      <Form.Item>{renderCaptcha()}</Form.Item>

                      <Form.Item>
                        <Form.Item name="remember" valuePropName="checked" noStyle>
                          <Checkbox>记住我</Checkbox>
                        </Form.Item>
                        <Link className="login-form-forgot" to="/auth/forgot-password">
                          忘记密码？
                        </Link>
                      </Form.Item>

                      <Form.Item>
                        <Button type="primary" htmlType="submit" loading={loading} block>
                          登录
                        </Button>
                      </Form.Item>

                      <Form.Item className="login-form-register">
                        还没有账号？<Link to="/auth/register">立即注册</Link>
                      </Form.Item>
                    </Form>
                  )
                },
                {
                  key: 'mobile',
                  label: '手机号登录',
                  children: (
                    <Form form={mobileForm} name="mobile-login" onFinish={(values) => submitLogin(values, 'mobile')} size="large">
                      <Form.Item
                        name="mobile"
                        rules={[
                          { required: true, message: '请输入手机号' },
                          { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' }
                        ]}
                      >
                        <Input prefix={<MobileOutlined />} placeholder="手机号" />
                      </Form.Item>

                      <Form.Item>
                        <Row gutter={8}>
                          <Col span={16}>
                            <Form.Item name="sms_code" noStyle rules={[{ required: true, message: '请输入短信验证码' }]}>
                              <Input prefix={<SafetyOutlined />} placeholder="短信验证码" />
                            </Form.Item>
                          </Col>
                          <Col span={8}>
                            <Button onClick={handleSendSmsCode} block>
                              获取验证码
                            </Button>
                          </Col>
                        </Row>
                      </Form.Item>

                      <Form.Item>{renderCaptcha()}</Form.Item>

                      <Form.Item>
                        <Button type="primary" htmlType="submit" loading={loading} block>
                          登录
                        </Button>
                      </Form.Item>

                      <Form.Item className="login-form-register">
                        还没有账号？<Link to="/auth/register">立即注册</Link>
                      </Form.Item>
                    </Form>
                  )
                }
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default LoginPage;
