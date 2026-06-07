// @ts-nocheck
import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { login as loginApi, logout as logoutApi, getUserInfo } from '@/api/auth';
import { getToken, setToken, removeToken } from '@/utils/auth';
import type { User, Role, LoginRequest, AuthContextType } from '@/types';

interface AuthState {
  user: User | null;
  permissions: string[];
  roles: Role[];
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

type AuthAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; permissions: string[]; roles: Role[] } }
  | { type: 'LOGOUT' }
  | { type: 'UPDATE_USER'; payload: User };

const initialState: AuthState = {
  user: null,
  permissions: [],
  roles: [],
  isAuthenticated: false,
  isLoading: true,
  error: null
};

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };
    
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        permissions: action.payload.permissions,
        roles: action.payload.roles,
        isAuthenticated: true,
        isLoading: false,
        error: null
      };
    
    case 'LOGOUT':
      return {
        ...initialState,
        isLoading: false
      };
    
    case 'UPDATE_USER':
      return {
        ...state,
        user: action.payload
      };
    
    default:
      return state;
  }
};

export const AuthContext = createContext<(AuthContextType & AuthState) | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // 鍒濆鍖栬璇佺姸鎬?
  useEffect(() => {
    const initAuth = async () => {
      const token = getToken();
      
      if (!token) {
        dispatch({ type: 'SET_LOADING', payload: false });
        return;
      }

      try {
        const response = await getUserInfo();
        
        if (response.success) {
          dispatch({
            type: 'LOGIN_SUCCESS',
            payload: {
              user: response.data.user_info,
              permissions: response.data.permissions || [],
              roles: response.data.roles || []
            }
          });
        } else {
          // Token 鏃犳晥锛屾竻闄ゆ湰鍦板瓨鍌?
          removeToken();
          dispatch({ type: 'LOGOUT' });
        }
      } catch (error) {
        console.error('鑾峰彇鐢ㄦ埛淇℃伅澶辫触:', error);
        removeToken();
        dispatch({ type: 'LOGOUT' });
      }
    };

    initAuth();
  }, []);

  const login = async (credentials: LoginRequest): Promise<void> => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      const response = await loginApi(credentials);
      
      if (response.success) {
        const { accessToken, userInfo } = response.data;
        
        // 淇濆瓨 token
        setToken(accessToken);
        
        // 鑾峰彇鐢ㄦ埛瀹屾暣淇℃伅锛堝寘鎷潈闄愬拰瑙掕壊锛?
        const userInfoResponse = await getUserInfo();
        
        if (userInfoResponse.success) {
          dispatch({
            type: 'LOGIN_SUCCESS',
            payload: {
              user: userInfoResponse.data.user_info,
              permissions: userInfoResponse.data.permissions || [],
              roles: userInfoResponse.data.roles || []
            }
          });
        } else {
          throw new Error('鑾峰彇鐢ㄦ埛淇℃伅澶辫触');
        }
      } else {
        throw new Error(response.message || '鐧诲綍澶辫触');
      }
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || '鐧诲綍澶辫触' });
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await logoutApi();
    } catch (error) {
      console.error('鐧诲嚭璇锋眰澶辫触:', error);
    } finally {
      removeToken();
      dispatch({ type: 'LOGOUT' });
    }
  };

  const refreshToken = async (): Promise<void> => {
    // 杩欓噷鍙互瀹炵幇 token 鍒锋柊閫昏緫
    // 鏆傛椂鐣欑┖锛屽悗缁彲浠ユ牴鎹渶瑕佸疄鐜?
  };

  const updateUser = (user: User): void => {
    dispatch({ type: 'UPDATE_USER', payload: user });
  };

  const contextValue: AuthContextType & AuthState = {
    ...state,
    login,
    logout,
    refreshToken,
    updateUser
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType & AuthState => {
  const context = useContext(AuthContext);
  
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
};