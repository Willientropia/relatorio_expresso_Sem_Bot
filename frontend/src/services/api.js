// frontend/src/services/api.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost/api', // Adjust this if your setup is different
  headers: {
    'Content-Type': 'application/json',
  },
});

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
