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

export const getResidentVitalsHistory = async (residentId: string, metric: string, range: string) => {
  const response = await api.get(`/analytics/residents/${residentId}/history/`, {
    params: { metric, range },
  });
  return response.data;
};

export const getAlertNotes = async (residentId: string) => {
  const response = await api.get(`/analytics/residents/${residentId}/notes/`);
  return response.data;
};

export const createAlertNote = async (residentId: string, note: string, alertType: string) => {
  const response = await api.post(`/analytics/residents/${residentId}/notes/`, {
    note,
    alert_type: alertType,
  });
  return response.data;
};

export const dismissAlert = async (residentId: string) => {
  const response = await api.post(`/analytics/residents/${residentId}/dismiss/`);
  return response.data;
};

export const toggleResidentActive = async (residentId: string) => {
  const response = await api.post(`/analytics/residents/${residentId}/toggle-active/`);
  return response.data;
};

export default api;
