import axios from 'axios';

// API base configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

// Create axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // Increased to 60 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create separate axios instance for file uploads with longer timeout
export const fileUploadClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for file uploads
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}> = [];

// Process failed requests queue
const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  
  failedQueue = [];
};

// Request interceptor to add auth token (for both clients)
const authInterceptor = (config: any) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

// Response interceptor to handle errors and token refresh
const errorInterceptor = async (error: any) => {
  const originalRequest = error.config;

  if (error.response?.status === 401 && !originalRequest._retry) {
    if (isRefreshing) {
      // If refresh is already in progress, queue this request
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(token => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return apiClient(originalRequest);
      }).catch(err => {
        return Promise.reject(err);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // Import authService here to avoid circular dependency
      const { authService } = await import('@/services/auth');
      
      // Try to refresh the token
      const response = await authService.refreshToken();
      const newToken = response.access_token;
      
      // Store new token
      authService.setToken(newToken);
      
      // Update authorization header for original request
      originalRequest.headers.Authorization = `Bearer ${newToken}`;
      
      // Process queued requests
      processQueue(null, newToken);
      
      // Retry original request
      return apiClient(originalRequest);
      
    } catch (refreshError) {
      // Refresh failed - clear tokens and redirect to login
      processQueue(refreshError, null);
      
      const { authService } = await import('@/services/auth');
      authService.clearTokens();
      
      // Redirect to login page if we're in the browser
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/signin';
      }
      
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }

  // For non-401 errors, just reject
  return Promise.reject(error);
};

// Apply interceptors to both clients
apiClient.interceptors.request.use(authInterceptor, (error) => Promise.reject(error));
apiClient.interceptors.response.use((response) => response, errorInterceptor);

fileUploadClient.interceptors.request.use(authInterceptor, (error) => Promise.reject(error));
fileUploadClient.interceptors.response.use((response) => response, errorInterceptor);

// API endpoints
export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    ME: '/auth/me',
  },
  // Documents
  DOCUMENTS: {
    LIST: '/documents',
    UPLOAD: '/documents',
    GET: (id: string) => `/documents/${id}`,
    PATCH: (id: string) => `/documents/${id}`,
    DELETE: (id: string) => `/documents/${id}`,
    CHUNKS: (id: string) => `/documents/${id}/chunks`,
    DOWNLOAD: (id: string) => `/documents/${id}/download-url`,
    QUALITY_METRICS: (id: string) => `/documents/${id}/quality-metrics`,
    PARSE_RESULTS: (id: string) => `/documents/${id}/parse-results`,
    UPDATE_STATUS: (id: string) => `/documents/${id}/update-status`,
  },
  // Users
  USERS: {
    LIST: '/users',
    CREATE: '/users',
    UPDATE: (id: string) => `/users/${id}`,
    DELETE: (id: string) => `/users/${id}`,
    ME: '/users/me',
  },
  // Admin
  ADMIN: {
    STATS: '/admin/stats',
    CONFIG: {
      CHUNKING: '/admin/config/chunking',
      EMBEDDING: '/admin/config/embedding',
      INDEX: '/admin/config/index',
      RETRIEVAL: '/admin/config/retrieval',
      LLM: '/admin/config/llm',
      PROMPTS: '/admin/config/prompts',
    },
  },
} as const;

export default apiClient; 