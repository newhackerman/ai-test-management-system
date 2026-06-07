import api from './api';
import type {
  LoginRequest,
  LoginResponse,
  ResendVerificationEmailRequest,
  ResendVerificationEmailResponse,
  UserSession,
  MFASetupData
} from '@/types';

interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  nickname?: string;
  phone?: string;
}

interface RegisterResponse {
  message: string;
  user_id?: number;
}

interface ForgotPasswordRequest {
  email: string;
}

interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password?: string;
}

interface MFASetupRequest {
  password?: string;
}

type MFASetupResponse = MFASetupData;

interface MFAVerifyRequest {
  verification_code: string;
}

interface MFAVerifyResponse {
  message: string;
  verified?: boolean;
}

interface CaptchaResponse {
  captcha_id: string;
  image_url?: string;
  image_base64?: string;
}

interface UserSessionsResponse {
  sessions: UserSession[];
}

interface LogoutRequest {
  refresh_token?: string;
  all_devices?: boolean;
}

interface VerifyEmailRequest {
  token: string;
}

interface VerifyEmailResponse {
  message: string;
  verified?: boolean;
}

class AuthService {
  async login(data: LoginRequest): Promise<LoginResponse> {
    return api.post('/auth/login', data);
  }

  async register(data: RegisterRequest): Promise<RegisterResponse> {
    return api.post('/auth/register', data);
  }

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    return api.post('/auth/refresh', { refresh_token: refreshToken });
  }

  async forgotPassword(data: ForgotPasswordRequest): Promise<{ message: string }> {
    return api.post('/auth/forgot-password', data);
  }

  async resetPassword(data: ResetPasswordRequest): Promise<{ message: string }> {
    return api.post('/auth/reset-password', data);
  }

  async changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
    return api.put('/auth/change-password', data);
  }

  async setupMFA(data: MFASetupRequest): Promise<MFASetupResponse> {
    return api.post('/auth/mfa/setup', data);
  }

  async verifyMFA(data: MFAVerifyRequest): Promise<MFAVerifyResponse> {
    return api.post('/auth/mfa/verify', data);
  }

  async disableMFA(data: { password: string }): Promise<{ message: string }> {
    return api.delete('/auth/mfa', { data });
  }

  async getCaptcha(): Promise<CaptchaResponse> {
    return api.get('/auth/captcha');
  }

  async getUserSessions(): Promise<UserSessionsResponse> {
    return api.get('/auth/sessions');
  }

  async logout(data?: LogoutRequest): Promise<{ message: string }> {
    return api.post('/auth/logout', data || {});
  }

  async verifyEmail(data: VerifyEmailRequest): Promise<VerifyEmailResponse> {
    return api.post('/auth/verify-email', data);
  }

  async resendVerificationEmail(data: ResendVerificationEmailRequest): Promise<ResendVerificationEmailResponse> {
    return api.post('/auth/resend-verification-email', data);
  }
}

export default new AuthService();
