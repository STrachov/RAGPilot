import { create } from 'zustand';
import { User } from '@/types/ragpilot';
import { authService, LoginCredentials } from '@/services/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  getCurrentUser: () => Promise<void>;
  clearError: () => void;
  checkAuth: () => void;
  refreshTokens: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  // Login action
  login: async (credentials: LoginCredentials) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.login(credentials);
      authService.setToken(response.access_token);
      
      // Store refresh token if provided
      if (response.refresh_token) {
        authService.setRefreshToken(response.refresh_token);
      }
      
      // Get user profile after login
      const user = await authService.getCurrentUser();
      
      set({ 
        user, 
        isAuthenticated: true, 
        isLoading: false,
        error: null 
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed';
      set({ 
        error: errorMessage, 
        isLoading: false,
        isAuthenticated: false,
        user: null 
      });
      throw error;
    }
  },

  // Logout action
  logout: async () => {
    set({ isLoading: true });
    try {
      await authService.logout();
    } catch (error) {
      // Continue with logout even if server call fails
      console.warn('Logout request failed:', error);
    } finally {
      // Clear all tokens and state
      authService.clearTokens();
      set({ 
        user: null, 
        isAuthenticated: false, 
        isLoading: false,
        error: null 
      });
    }
  },

  // Get current user
  getCurrentUser: async () => {
    if (!authService.isAuthenticated()) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    set({ isLoading: true });
    try {
      const user = await authService.getCurrentUser();
      set({ 
        user, 
        isAuthenticated: true, 
        isLoading: false,
        error: null 
      });
    } catch (error) {
      // Token might be expired or invalid
      // Don't clear tokens here - let the API interceptor handle refresh
      set({ 
        user: null, 
        isAuthenticated: false, 
        isLoading: false,
        error: null 
      });
    }
  },

  // Refresh tokens manually
  refreshTokens: async (): Promise<boolean> => {
    try {
      const response = await authService.refreshToken();
      authService.setToken(response.access_token);
      
      // Update auth state
      set({ isAuthenticated: true, error: null });
      
      return true;
    } catch (error) {
      // Refresh failed - clear tokens and logout
      authService.clearTokens();
      set({ 
        user: null, 
        isAuthenticated: false, 
        error: null 
      });
      return false;
    }
  },

  // Clear error
  clearError: () => set({ error: null }),

  // Check auth status (for app initialization)
  checkAuth: () => {
    const isAuthenticated = authService.isAuthenticated();
    if (isAuthenticated) {
      // Set authenticated state but don't immediately fetch user
      // Let the API interceptor handle any token refresh if needed
      set({ isAuthenticated: true });
      
      // Try to get user profile, but don't fail if it doesn't work
      get().getCurrentUser().catch(() => {
        // Silently fail - the API interceptor will handle token refresh
      });
    } else {
      set({ isAuthenticated: false, user: null });
    }
  },
})); 