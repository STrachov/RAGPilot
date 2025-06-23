import { apiClient, API_ENDPOINTS } from '@/lib/api';
import { User } from '@/types/ragpilot';

export interface LoginCredentials {
  username: string; // FastAPI typically uses 'username' for OAuth2PasswordRequestForm
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user?: User;
  refresh_token?: string; // Add refresh token to response
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
}

export const authService = {
  // Login with username/password
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    // FastAPI OAuth2PasswordRequestForm expects application/x-www-form-urlencoded
    const params = new URLSearchParams();
    params.append('username', credentials.username);
    params.append('password', credentials.password);

    const { data } = await apiClient.post(API_ENDPOINTS.AUTH.LOGIN, params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return data;
  },

  // Refresh access token using refresh token
  async refreshToken(): Promise<RefreshTokenResponse> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const { data } = await apiClient.post(API_ENDPOINTS.AUTH.REFRESH, {
      refresh_token: refreshToken
    });
    return data;
  },

  // Logout
  async logout(): Promise<{ message: string }> {
    const { data } = await apiClient.post(API_ENDPOINTS.AUTH.LOGOUT);
    return data;
  },

  // Get current user profile
  async getCurrentUser(): Promise<User> {
    const { data } = await apiClient.get(API_ENDPOINTS.USERS.ME);
    return data;
  },

  // Access token management
  setToken(token: string): void {
    localStorage.setItem('access_token', token);
  },

  getToken(): string | null {
    return localStorage.getItem('access_token');
  },

  removeToken(): void {
    localStorage.removeItem('access_token');
  },

  // Refresh token management
  setRefreshToken(token: string): void {
    localStorage.setItem('refresh_token', token);
  },

  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  },

  removeRefreshToken(): void {
    localStorage.removeItem('refresh_token');
  },

  // Clear all tokens
  clearTokens(): void {
    this.removeToken();
    this.removeRefreshToken();
  },

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return !!this.getToken();
  },
}; 