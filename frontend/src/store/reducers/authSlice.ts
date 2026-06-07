import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';

// 用户信息类型
interface UserInfo {
  user_id: number;
  username: string;
  email: string;
  nickname?: string;
  avatar?: string;
  roles: string[];
  permissions: string[];
  is_active: boolean;
  is_email_verified: boolean;
  is_mfa_enabled: boolean;
}

// 认证状态
interface AuthState {
  isAuthenticated: boolean;
  userInfo: UserInfo | null;
  token: string | null;
  refreshToken: string | null;
  loading: boolean;
  error: string | null;
}

// 初始状态
const initialState: AuthState = {
  isAuthenticated: false,
  userInfo: null,
  token: null,
  refreshToken: null,
  loading: false,
  error: null,
};

// 认证 slice
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    // 登录请求
    loginRequest: (state, action: PayloadAction<{ username: string; password: string; captcha?: string; captcha_key?: string }>) => {
      state.loading = true;
      state.error = null;
    },
    // 登录成功
    loginSuccess: (state, action: PayloadAction<{ token: string; refreshToken: string; user: UserInfo }>) => {
      state.isAuthenticated = true;
      state.token = action.payload.token;
      state.refreshToken = action.payload.refreshToken;
      state.userInfo = action.payload.user;
      state.loading = false;
      state.error = null;
    },
    // 登录失败
    loginFailure: (state, action: PayloadAction<string>) => {
      state.isAuthenticated = false;
      state.token = null;
      state.refreshToken = null;
      state.userInfo = null;
      state.loading = false;
      state.error = action.payload;
    },
    // 注册请求
    registerRequest: (state, action: PayloadAction<{ username: string; email: string; password: string; captcha: string; captcha_key: string }>) => {
      state.loading = true;
      state.error = null;
    },
    // 注册成功
    registerSuccess: (state) => {
      state.loading = false;
      state.error = null;
    },
    // 注册失败
    registerFailure: (state, action: PayloadAction<string>) => {
      state.loading = false;
      state.error = action.payload;
    },
    // 登出
    logout: (state) => {
      state.isAuthenticated = false;
      state.userInfo = null;
      state.token = null;
      state.refreshToken = null;
      state.loading = false;
      state.error = null;
    },
    // 刷新令牌请求
    refreshTokenRequest: (state) => {
      state.loading = true;
      state.error = null;
    },
    // 刷新令牌成功
    refreshTokenSuccess: (state, action: PayloadAction<{ token: string; refreshToken: string }>) => {
      state.token = action.payload.token;
      state.refreshToken = action.payload.refreshToken;
      state.loading = false;
      state.error = null;
    },
    // 刷新令牌失败
    refreshTokenFailure: (state, action: PayloadAction<string>) => {
      state.isAuthenticated = false;
      state.token = null;
      state.refreshToken = null;
      state.userInfo = null;
      state.loading = false;
      state.error = action.payload;
    },
    // 更新用户信息
    updateUserInfo: (state, action: PayloadAction<Partial<UserInfo>>) => {
      if (state.userInfo) {
        state.userInfo = { ...state.userInfo, ...action.payload };
      }
    },
    // 清除错误
    clearError: (state) => {
      state.error = null;
    },
    // 重置状态
    resetAuthState: () => initialState,
  },
});

// 导出 actions
export const {
  loginRequest,
  loginSuccess,
  loginFailure,
  registerRequest,
  registerSuccess,
  registerFailure,
  logout,
  refreshTokenRequest,
  refreshTokenSuccess,
  refreshTokenFailure,
  updateUserInfo,
  clearError,
  resetAuthState,
} = authSlice.actions;

// 导出 reducer
const authReducer = authSlice.reducer;

// 添加 selector 函数
export const selectUserInfo = (state: { auth: AuthState }) => state.auth.userInfo;

// 持久化配置
const persistConfig = {
  key: 'auth',
  storage,
  whitelist: ['isAuthenticated', 'userInfo', 'token', 'refreshToken'],
};

// 持久化 reducer
export default persistReducer(persistConfig, authReducer);