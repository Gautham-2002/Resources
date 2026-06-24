# Part 7.2: API Integration Patterns

## What You'll Learn

- Structuring an API layer in React applications
- Type-safe API calls with TypeScript
- Environment variable management
- Authentication patterns (JWT, Bearer tokens)
- Refresh token rotation
- Error handling strategies at the API layer
- API response normalization

---

## Table of Contents

1. [API Layer Architecture](#api-layer-architecture)
2. [Type-Safe API Client](#type-safe-api-client)
3. [Environment Variables](#environment-variables)
4. [Authentication Patterns](#authentication-patterns)
5. [Refresh Token Pattern](#refresh-token-pattern)
6. [Error Handling Strategy](#error-handling-strategy)
7. [API Response Normalization](#api-response-normalization)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Resources](#resources)

---

## API Layer Architecture

### Folder Structure

```
src/
  services/
    api/
      client.ts          # Axios instance with interceptors
      types.ts           # Shared API types
      endpoints/
        users.ts         # User-related API calls
        products.ts      # Product-related API calls
        auth.ts          # Authentication API calls
```

### API Client Setup

```typescript
// services/api/client.ts
import axios, { type InternalAxiosRequestConfig } from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach auth token
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;
```

### Typed API Endpoints

```typescript
// services/api/types.ts
export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

// services/api/endpoints/users.ts
import apiClient from '../client';
import type { PaginatedResponse } from '../types';
import type { User, CreateUserDTO, UpdateUserDTO } from '@/types/user';

export const usersApi = {
  list: async (params?: { page?: number; limit?: number; search?: string }) => {
    const { data } = await apiClient.get<PaginatedResponse<User>>('/users', { params });
    return data;
  },

  getById: async (id: string) => {
    const { data } = await apiClient.get<User>(`/users/${id}`);
    return data;
  },

  create: async (payload: CreateUserDTO) => {
    const { data } = await apiClient.post<User>('/users', payload);
    return data;
  },

  update: async (id: string, payload: UpdateUserDTO) => {
    const { data } = await apiClient.patch<User>(`/users/${id}`, payload);
    return data;
  },

  delete: async (id: string) => {
    await apiClient.delete(`/users/${id}`);
  },
};
```

---

## Type-Safe API Client

### Generic Request Function

```typescript
// services/api/client.ts
import { z } from 'zod';

// Validate API responses with Zod at runtime
async function typedGet<T extends z.ZodType>(
  url: string,
  schema: T,
  config?: AxiosRequestConfig
): Promise<z.infer<T>> {
  const { data } = await apiClient.get(url, config);
  return schema.parse(data); // Runtime validation!
}

// Usage
const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string().email(),
});

const user = await typedGet('/users/1', UserSchema);
// user is fully typed AND validated at runtime
```

---

## Environment Variables

### Setup

```bash
# .env.development
VITE_API_URL=http://localhost:3001/api
VITE_APP_NAME=MyApp Dev
VITE_ENABLE_MOCKS=true

# .env.production
VITE_API_URL=https://api.myapp.com
VITE_APP_NAME=MyApp
VITE_ENABLE_MOCKS=false

# .env.local (never committed, overrides everything)
VITE_API_URL=http://localhost:3001/api
```

### Type-Safe Environment Variables

```typescript
// config/env.ts
import { z } from 'zod';

const envSchema = z.object({
  VITE_API_URL: z.string().url(),
  VITE_APP_NAME: z.string().default('Frontend App'),
  VITE_ENABLE_MOCKS: z.coerce.boolean().default(false),
  MODE: z.enum(['development', 'production', 'test']),
});

export const env = envSchema.parse(import.meta.env);

// Usage: env.VITE_API_URL (typed, validated)
```

---

## Authentication Patterns

### JWT Authentication Flow

```typescript
// services/api/endpoints/auth.ts
interface LoginRequest {
  email: string;
  password: string;
}

interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

export const authApi = {
  login: async (credentials: LoginRequest) => {
    const { data } = await apiClient.post<AuthTokens>('/auth/login', credentials);

    // Store tokens
    localStorage.setItem('access_token', data.accessToken);
    localStorage.setItem('refresh_token', data.refreshToken);

    return data;
  },

  logout: async () => {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  },

  getMe: async () => {
    const { data } = await apiClient.get<User>('/auth/me');
    return data;
  },
};
```

---

## Refresh Token Pattern

### Automatic Token Refresh

```typescript
// services/api/client.ts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: any) => void;
  reject: (reason: any) => void;
}> = [];

const processQueue = (error: any, token: string | null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue this request until refresh completes
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return apiClient(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = localStorage.getItem('refresh_token');
      const { data } = await axios.post(`${import.meta.env.VITE_API_URL}/auth/refresh`, {
        refreshToken,
      });

      localStorage.setItem('access_token', data.accessToken);
      localStorage.setItem('refresh_token', data.refreshToken);

      apiClient.defaults.headers.common.Authorization = `Bearer ${data.accessToken}`;
      processQueue(null, data.accessToken);

      originalRequest.headers.Authorization = `Bearer ${data.accessToken}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
```

---

## Error Handling Strategy

### Centralized Error Handler

```typescript
// services/api/errorHandler.ts
import { AxiosError } from 'axios';
import type { ApiError } from './types';

export class AppError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string,
    public details?: Record<string, string[]>
  ) {
    super(message);
    this.name = 'AppError';
  }
}

export function handleApiError(error: unknown): never {
  if (error instanceof AxiosError) {
    const apiError = error.response?.data as ApiError | undefined;

    switch (error.response?.status) {
      case 400:
        throw new AppError(
          apiError?.message || 'Invalid request',
          400,
          apiError?.code,
          apiError?.details
        );
      case 401:
        throw new AppError('Please log in again', 401, 'UNAUTHORIZED');
      case 403:
        throw new AppError('You do not have permission', 403, 'FORBIDDEN');
      case 404:
        throw new AppError('Resource not found', 404, 'NOT_FOUND');
      case 422:
        throw new AppError(
          'Validation failed',
          422,
          'VALIDATION_ERROR',
          apiError?.details
        );
      case 429:
        throw new AppError('Too many requests, please try again later', 429, 'RATE_LIMITED');
      default:
        if (error.response && error.response.status >= 500) {
          throw new AppError('Server error, please try again later', error.response.status);
        }
    }

    if (!error.response) {
      throw new AppError('Network error — check your connection', 0, 'NETWORK_ERROR');
    }
  }

  throw new AppError('An unexpected error occurred');
}
```

---

## API Response Normalization

### Consistent Response Shape

```typescript
// services/api/normalizer.ts

// Normalize different API response shapes into consistent format
interface NormalizedResponse<T> {
  data: T;
  pagination?: {
    total: number;
    page: number;
    perPage: number;
    totalPages: number;
  };
}

function normalizeListResponse<T>(response: any): NormalizedResponse<T[]> {
  // Handle different API formats

  // Format 1: { data: [...], meta: { total, page, limit } }
  if (response.data && response.meta) {
    return {
      data: response.data,
      pagination: {
        total: response.meta.total,
        page: response.meta.page,
        perPage: response.meta.limit,
        totalPages: Math.ceil(response.meta.total / response.meta.limit),
      },
    };
  }

  // Format 2: { results: [...], count: number }
  if (response.results) {
    return {
      data: response.results,
      pagination: { total: response.count, page: 1, perPage: response.count, totalPages: 1 },
    };
  }

  // Format 3: Just an array
  if (Array.isArray(response)) {
    return { data: response };
  }

  return { data: response };
}
```

---

## Common Patterns & Best Practices

### Pattern 1: API Service Barrel Export

```typescript
// services/api/index.ts
export { default as apiClient } from './client';
export { usersApi } from './endpoints/users';
export { productsApi } from './endpoints/products';
export { authApi } from './endpoints/auth';
export type { PaginatedResponse, ApiError } from './types';
```

### Pattern 2: Request/Response Logging (Dev Only)

```typescript
if (import.meta.env.DEV) {
  apiClient.interceptors.request.use((config) => {
    console.log(`🚀 ${config.method?.toUpperCase()} ${config.url}`, config.params || '');
    return config;
  });

  apiClient.interceptors.response.use(
    (response) => {
      console.log(`✅ ${response.status} ${response.config.url}`, response.data);
      return response;
    },
    (error) => {
      console.error(`❌ ${error.response?.status} ${error.config?.url}`, error.response?.data);
      return Promise.reject(error);
    }
  );
}
```

### Pattern 3: MSW Integration for Development

```typescript
// mocks/browser.ts
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);

// main.tsx
async function enableMocking() {
  if (import.meta.env.VITE_ENABLE_MOCKS !== 'true') return;
  const { worker } = await import('./mocks/browser');
  return worker.start({ onUnhandledRequest: 'bypass' });
}

enableMocking().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
});
```

---

## Common Pitfalls

### Pitfall 1: Hardcoding API URLs

```typescript
// ❌ Hardcoded
axios.get('http://localhost:3001/api/users');

// ✅ Environment variable + instance
apiClient.get('/users'); // baseURL from env
```

### Pitfall 2: Not Typing API Responses

```typescript
// ❌ Response is `any`
const { data } = await apiClient.get('/users');
data.forEach(u => u.naem); // Typo not caught!

// ✅ Typed response
const { data } = await apiClient.get<User[]>('/users');
data.forEach(u => u.name); // TypeScript catches typos
```

---

## Resources

- **Axios Best Practices:** https://axios-http.com/docs/best-practices
- **JWT.io:** https://jwt.io/
- **MSW Documentation:** https://mswjs.io/
- **OAuth 2.0 Simplified:** https://aaronparecki.com/oauth-2-simplified/

---

**Next:** [Part 8.1: TanStack Query Fundamentals](../part-08/08-tanstack-query-fundamentals.md)
