import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const login = async (email: string, password: string) => {
  const response = await api.post('/login/', { email, password });
  return response.data;
};

export const register = async (data: any) => {
  const response = await api.post('/register/', data);
  return response.data;
};

export const getUserProfile = async () => {
  const response = await api.get('/user/');
  return response.data;
};

export const getDashboardConfig = async () => {
  const response = await api.get('/analytics/config/');
  return response.data;
};

export const getResidents = async () => {
  const response = await api.get('/analytics/residents/');
  return response.data;
};

export default api;
