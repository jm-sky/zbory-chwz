import axios from 'axios'
import { authInterceptor } from './auth.interceptor'
import { errorResponseInterceptor } from './error.interceptor'
import { localeInterceptor } from './locale.interceptor'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: Add authentication token
apiClient.interceptors.request.use(authInterceptor)

// Request interceptor: Add current locale so backend responses match the user's language
apiClient.interceptors.request.use(localeInterceptor)

// Response interceptor: Handle errors (401, etc.)
apiClient.interceptors.response.use(
  (response) => response,
  errorResponseInterceptor,
)
