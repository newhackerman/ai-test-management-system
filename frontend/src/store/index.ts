import { configureStore, combineReducers } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import { createReduxHistoryContext } from 'redux-first-history';
import { createBrowserHistory } from 'history';
import authReducer from './reducers/authSlice';
import themeReducer from './reducers/themeSlice';
import userReducer from './reducers/userSlice';
import roleReducer from './reducers/roleSlice';
import permissionReducer from './reducers/permissionSlice';

// 创建浏览器历史记录
export const history = createBrowserHistory();

// 创建 Redux First History 上下文
const {
  routerMiddleware,
  routerReducer
} = createReduxHistoryContext({ 
  history,
});

// 组合所有reducer
const rootReducer = combineReducers({
  auth: authReducer,
  theme: themeReducer,
  user: userReducer,
  role: roleReducer,
  permission: permissionReducer,
  router: routerReducer,
});

// Redux Persist 配置
const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth', 'theme'], // 只持久化 auth 和 theme reducer
};

// 创建持久化 reducer
const persistedReducer = persistReducer(persistConfig, rootReducer);

// 配置 store
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }).concat(routerMiddleware),
  devTools: process.env.NODE_ENV !== 'production',
});

// 创建持久化 store
export const persistor = persistStore(store);

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;