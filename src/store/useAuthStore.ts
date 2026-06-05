import { create } from 'zustand';
import type { UserInfo, RoleInfo } from '../types';
import { authApi } from '../services/api';

interface AuthState {
  user: UserInfo | null;
  roles: RoleInfo[];
  users: Record<string, { role: string; name: string }>;
  loading: boolean;
  error: string | null;
  fetchCurrentUser: () => Promise<void>;
  fetchRoles: () => Promise<void>;
  fetchUsers: () => Promise<void>;
  switchRole: (role: string, username: string) => Promise<boolean>;
  hasPermission: (permission: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  roles: [],
  users: {},
  loading: false,
  error: null,

  fetchCurrentUser: async () => {
    try {
      set({ loading: true });
      const res = await authApi.getCurrentRole();
      if (res.success && res.data) {
        set({ user: res.data });
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '获取用户信息失败' });
    } finally {
      set({ loading: false });
    }
  },

  fetchRoles: async () => {
    try {
      const res = await authApi.getRoles();
      if (res.success && res.data) {
        set({ roles: res.data });
      }
    } catch (e) {
      console.error('Failed to fetch roles:', e);
    }
  },

  fetchUsers: async () => {
    try {
      const res = await authApi.getUsers();
      if (res.success && res.data) {
        set({ users: res.data });
      }
    } catch (e) {
      console.error('Failed to fetch users:', e);
    }
  },

  switchRole: async (role: string, username: string) => {
    try {
      set({ loading: true, error: null });
      const res = await authApi.switchRole({ role, username });
      if (res.success && res.data) {
        set({ user: res.data });
        return true;
      }
      return false;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '切换角色失败' });
      return false;
    } finally {
      set({ loading: false });
    }
  },

  hasPermission: (permission: string) => {
    const user = get().user;
    if (!user) return false;
    return user.permissions.includes(permission);
  },
}));
