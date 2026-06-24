# Part 7.1: Axios Fundamentals

## What You'll Learn

- Why Axios over the Fetch API
- Installation and configuration
- Request/response interceptors
- Error handling strategies
- Timeout and retry logic
- Request cancellation with AbortController
- Creating a robust API client

---

## Table of Contents

1. [Why Axios](#why-axios)
2. [Basic Usage](#basic-usage)
3. [Creating an Axios Instance](#creating-an-axios-instance)
4. [Request Configuration](#request-configuration)
5. [Interceptors](#interceptors)
6. [Error Handling](#error-handling)
7. [Request Cancellation](#request-cancellation)
8. [Timeout & Retry](#timeout--retry)
9. [File Upload & Download](#file-upload--download)
10. [Common Patterns & Best Practices](#common-patterns--best-practices)
11. [Common Pitfalls](#common-pitfalls)
12. [Resources](#resources)

---

## Why Axios

### Axios vs Fetch API

```typescript
// Fetch API issues:
// 1. Doesn't reject on HTTP errors (404, 500 are "successful" requests)
// 2. No built-in timeout
// 3. No interceptors
// 4. No request/response transformation
// 5. Verbose error handling

// Fetch example (verbose):
try {
  const response = await fetch('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: 'John' }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`); // Must check manually!
  }

  const data = await response.json(); // Must parse manually!
} catch (error) {
  // Network errors AND HTTP errors mixed
}

// Axios equivalent (clean):
try {
  const { data } = await axios.post('/api/users', { name: 'John' });
  // Auto-throws on 4xx/5xx
  // Auto-parses JSON
  // Auto-sets Content-Type
} catch (error) {
  if (error.response) {
    // Server responded with error (4xx, 5xx)
  } else if (error.request) {
    // No response received (network error)
  }
}
```

### Key Advantages

```
1. Automatic JSON transformation
2. HTTP error rejection (4xx/5xx throw errors)
3. Request/response interceptors
4. Built-in timeout support
5. Request cancellation
6. Progress events for uploads
7. XSRF protection
8. Works in Node.js and browsers
```

---

## Basic Usage

### Installation

```bash
pnpm add axios
```

### CRUD Operations

```typescript
import axios from 'axios';

// GET
const { data: users } = await axios.get('/api/users');
const { data: user } = await axios.get('/api/users/1');

// GET with query params
const { data: filtered } = await axios.get('/api/users', {
  params: { role: 'admin', page: 1, limit: 10 },
});
// Request: GET /api/users?role=admin&page=1&limit=10

// POST
const { data: newUser } = await axios.post('/api/users', {
  name: 'John',
  email: 'john@example.com',
});

// PUT (full replace)
const { data: updated } = await axios.put('/api/users/1', {
  name: 'John Updated',
  email: 'john@example.com',
});

// PATCH (partial update)
const { data: patched } = await axios.patch('/api/users/1', {
  name: 'John Patched',
});

// DELETE
await axios.delete('/api/users/1');
```

---

## Creating an Axios Instance

### The Standard Pattern

```typescript
// services/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:3001/api',
  timeout: 10000, // 10 seconds
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

export default apiClient;
```

### Usage

```typescript
// services/api/users.ts
import apiClient from './client';

export const usersApi = {
  getAll: (params?: { page: number; limit: number }) =>
    apiClient.get('/users', { params }),

  getById: (id: number) =>
    apiClient.get(`/users/${id}`),

  create: (data: CreateUserDTO) =>
    apiClient.post('/users', data),

  update: (id: number, data: UpdateUserDTO) =>
    apiClient.patch(`/users/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/users/${id}`),
};
```

---

## Interceptors

### Request Interceptor (Add Auth Token)

```typescript
// Add auth token to every request
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
```

### Response Interceptor (Handle Errors)

```typescript
// Handle common response errors
apiClient.interceptors.response.use(
  (response) => {
    // Any 2xx response
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // 401: Token expired — try refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const { data } = await axios.post('/api/auth/refresh', {
          refreshToken: localStorage.getItem('refresh_token'),
        });

        localStorage.setItem('auth_token', data.accessToken);
        originalRequest.headers.Authorization = `Bearer ${data.accessToken}`;

        return apiClient(originalRequest); // Retry original request
      } catch (refreshError) {
        // Refresh failed — force logout
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    // 403: Forbidden
    if (error.response?.status === 403) {
      console.error('Access denied');
    }

    // 500: Server error
    if (error.response?.status >= 500) {
      console.error('Server error — please try again later');
    }

    return Promise.reject(error);
  }
);
```

---

## Error Handling

### Typed Error Handling

```typescript
import { AxiosError } from 'axios';

interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

async function createUser(data: CreateUserDTO) {
  try {
    const response = await apiClient.post('/users', data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;

      if (axiosError.response) {
        // Server responded with error
        const { status, data } = axiosError.response;
        console.error(`API Error ${status}:`, data.message);

        if (status === 422 && data.details) {
          // Validation errors
          return { errors: data.details };
        }
      } else if (axiosError.request) {
        // No response (network error)
        console.error('Network error — check your connection');
      }
    }
    throw error;
  }
}
```

---

## Request Cancellation

```typescript
// Using AbortController
function SearchComponent() {
  const controllerRef = useRef<AbortController | null>(null);

  const search = async (query: string) => {
    // Cancel previous request
    controllerRef.current?.abort();

    // Create new controller
    controllerRef.current = new AbortController();

    try {
      const { data } = await apiClient.get('/search', {
        params: { q: query },
        signal: controllerRef.current.signal,
      });
      return data;
    } catch (error) {
      if (axios.isCancel(error)) {
        console.log('Request cancelled');
        return null;
      }
      throw error;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => controllerRef.current?.abort();
  }, []);
}
```

---

## Timeout & Retry

### Retry Logic

```typescript
import axios, { AxiosError } from 'axios';

async function requestWithRetry<T>(
  fn: () => Promise<T>,
  retries = 3,
  delay = 1000
): Promise<T> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === retries) throw error;

      const axiosError = error as AxiosError;
      // Only retry on network errors or 5xx
      if (axiosError.response && axiosError.response.status < 500) {
        throw error; // Don't retry 4xx errors
      }

      // Exponential backoff
      const waitTime = delay * Math.pow(2, attempt);
      console.log(`Retry attempt ${attempt + 1} in ${waitTime}ms`);
      await new Promise((resolve) => setTimeout(resolve, waitTime));
    }
  }
  throw new Error('Max retries exceeded');
}

// Usage
const users = await requestWithRetry(() => apiClient.get('/users'));
```

---

## File Upload & Download

### Upload with Progress

```typescript
async function uploadFile(
  file: File,
  onProgress: (percent: number) => void
) {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await apiClient.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const percent = Math.round(
        (progressEvent.loaded * 100) / (progressEvent.total || 1)
      );
      onProgress(percent);
    },
  });

  return data;
}

// Usage in component
function UploadButton() {
  const [progress, setProgress] = useState(0);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    await uploadFile(file, setProgress);
  };

  return (
    <div>
      <input type="file" onChange={handleUpload} />
      {progress > 0 && (
        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
          <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
}
```

---

## Common Patterns & Best Practices

### Pattern 1: Type-Safe API Layer

```typescript
// services/api/types.ts
interface ApiResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
    limit: number;
  };
}

// services/api/users.ts
export const usersApi = {
  getAll: async (params?: PaginationParams) => {
    const { data } = await apiClient.get<ApiResponse<User[]>>('/users', { params });
    return data;
  },
};
```

### Pattern 2: Environment-Based Configuration

```typescript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: import.meta.env.PROD ? 10000 : 30000, // Longer timeout in dev
});
```

### Pattern 3: Request Deduplication

```typescript
const pendingRequests = new Map<string, Promise<any>>();

function deduplicatedGet<T>(url: string, config?: any): Promise<T> {
  const key = `${url}:${JSON.stringify(config?.params)}`;

  if (pendingRequests.has(key)) {
    return pendingRequests.get(key)!;
  }

  const promise = apiClient.get<T>(url, config)
    .then(res => res.data)
    .finally(() => pendingRequests.delete(key));

  pendingRequests.set(key, promise);
  return promise;
}
```

---

## Common Pitfalls

### Pitfall 1: Not Creating an Instance

```typescript
// ❌ Using axios directly (no base URL, no interceptors)
axios.get('http://localhost:3001/api/users');

// ✅ Use a configured instance
apiClient.get('/users');
```

### Pitfall 2: Not Handling All Error Types

```typescript
// ❌ Only checking response
catch (error) {
  console.log(error.response.data); // Crashes if no response!
}

// ✅ Check all error types
catch (error) {
  if (axios.isAxiosError(error)) {
    if (error.response) { /* Server error */ }
    else if (error.request) { /* Network error */ }
    else { /* Setup error */ }
  }
}
```

### Pitfall 3: Memory Leaks from Uncancelled Requests

```typescript
// ❌ Component unmounts but request continues
useEffect(() => {
  apiClient.get('/data').then(setData);
}, []);

// ✅ Cancel on unmount
useEffect(() => {
  const controller = new AbortController();
  apiClient.get('/data', { signal: controller.signal }).then(setData);
  return () => controller.abort();
}, []);
```

---

## Resources

- **Axios Documentation:** https://axios-http.com/
- **Axios Interceptors:** https://axios-http.com/docs/interceptors
- **MDN AbortController:** https://developer.mozilla.org/en-US/docs/Web/API/AbortController
- **HTTP Status Codes:** https://developer.mozilla.org/en-US/docs/Web/HTTP/Status

---

**Next:** [Part 7.2: API Integration Patterns](./07-api-integration-patterns.md)
