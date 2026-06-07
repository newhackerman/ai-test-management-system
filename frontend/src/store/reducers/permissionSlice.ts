import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface PermissionState {
  permissions: any[];
  loading: boolean;
  error: string | null;
}

const initialState: PermissionState = {
  permissions: [],
  loading: false,
  error: null,
};

const permissionSlice = createSlice({
  name: 'permission',
  initialState,
  reducers: {
    setPermissions: (state, action: PayloadAction<any[]>) => {
      state.permissions = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const { setPermissions, setLoading, setError } = permissionSlice.actions;
export default permissionSlice.reducer;