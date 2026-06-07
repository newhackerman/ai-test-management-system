// @ts-nocheck
import { combineReducers } from '@reduxjs/toolkit';
import { routerReducer } from 'redux-first-history';
import authReducer from './authSlice';
import themeReducer from './themeSlice';
import userReducer from './userSlice';
import roleReducer from './roleSlice';
import permissionReducer from './permissionSlice';

const rootReducer = combineReducers({
  router: routerReducer,
  auth: authReducer,
  theme: themeReducer,
  user: userReducer,
  role: roleReducer,
  permission: permissionReducer,
});

export default rootReducer;
export type RootState = ReturnType<typeof rootReducer>;