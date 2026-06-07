// @ts-nocheck
import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAppSelector } from '@/store/hooks';
import { selectIsAuthenticated } from '@/store/reducers/authSlice';

interface AuthGuardProps {
  children: React.ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isLoading = useAppSelector((state) => state.auth.loading);

  useEffect(() => {
    console.log('AuthGuard妫€鏌ヨ璇佺姸鎬?', isAuthenticated); // 娣诲姞鏃ュ織浠ヤ究璋冭瘯
    if (!isLoading && !isAuthenticated) {
      // 淇濆瓨褰撳墠璺緞锛屼互渚跨櫥褰曞悗璺宠浆鍥炴潵
      navigate('/login', {
        state: { from: location.pathname },
        replace: true,
      });
    }
  }, [isAuthenticated, isLoading, navigate, location]);

  if (isLoading) {
    return (
      <div className="flex-center full-height">
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // 鍦?useEffect 涓鐞嗛噸瀹氬悜
  }

  return <>{children}</>;
};

export default AuthGuard;