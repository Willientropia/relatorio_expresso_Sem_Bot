// frontend/src/services/api.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api', // Usando caminho relativo para que funcione com qualquer IP
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // Add a timeout to prevent hanging requests
});

// Adiciona um interceptador para incluir o token de acesso em todas as requisições
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle common errors
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    if (error.message === 'Network Error') {
      console.error('Network Error: Cannot connect to the backend server. Please check if the server is running.');
    }
    return Promise.reject(error);
  }
);

export { apiClient }; // Use a named export

export const fetchTasks = (customerId) => {
  return apiClient.get(`/customers/${customerId}/faturas/tasks/`);
};

export const fetchFaturas = (customerId) => {
  return apiClient.get(`/customers/${customerId}/faturas/`);
};

export const fetchLogs = (customerId) => {
  return apiClient.get(`/customers/${customerId}/faturas/logs/`);
};

export const startImport = (customerId) => {
  return apiClient.post(`/customers/${customerId}/faturas/import/`);
};

export const fetchCustomer = (customerId) => {
  return apiClient.get(`/customers/${customerId}/`);
};

export const fetchUCs = (customerId) => {
  return apiClient.get(`/customers/${customerId}/ucs/`);
};

export const addUC = (customerId, newUc) => {
  return apiClient.post(`/customers/${customerId}/ucs/`, newUc);
};

export const deleteUC = (customerId, ucId) => {
  return apiClient.delete(`/customers/${customerId}/ucs/${ucId}/`);
};

export const toggleUCStatus = (customerId, ucId) => {
  return apiClient.post(`/customers/${customerId}/ucs/${ucId}/toggle/`);
};

export const updateUC = (customerId, ucId, data) => {
  return apiClient.put(`/customers/${customerId}/ucs/${ucId}/`, data);
};

export const fetchCustomers = () => {
  return apiClient.get('/customers/');
};

export const addCustomer = (customerData) => {
  return apiClient.post('/customers/', customerData);
};

export const deleteCustomer = (customerId) => {
  return apiClient.delete(`/customers/${customerId}/`);
};
