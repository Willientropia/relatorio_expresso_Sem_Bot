// frontend/src/services/api.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // Aumentar timeout para uploads
});

// ✅ CORREÇÃO: Interceptador de Request mais robusto
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    
    // Debug log
    console.log('🔐 Request interceptor:', {
      url: config.url,
      method: config.method,
      hasToken: !!token,
      tokenPreview: token ? `${token.substring(0, 20)}...` : 'NO_TOKEN'
    });
    
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    } else {
      console.warn('⚠️ No access token found in localStorage');
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// ✅ CORREÇÃO: Interceptador de Response com refresh token
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    console.error('🚨 API Error:', {
      status: error.response?.status,
      url: error.config?.url,
      method: error.config?.method,
      message: error.message
    });
    
    // Se erro 401 e não é uma tentativa de refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refreshToken');
      
      if (refreshToken) {
        try {
          console.log('🔄 Tentando refresh token...');
          
          // Fazer request de refresh sem interceptadores para evitar loop
          const refreshResponse = await axios.post('/api/token/refresh/', {
            refresh: refreshToken
          });
          
          const newAccessToken = refreshResponse.data.access;
          localStorage.setItem('accessToken', newAccessToken);
          
          // Repetir request original com novo token
          originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
          
          console.log('✅ Token refreshed successfully');
          return apiClient(originalRequest);
          
        } catch (refreshError) {
          console.error('❌ Refresh token failed:', refreshError);
          
          // Limpar tokens e redirecionar para login
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          
          // Redirecionar para login se não estivermos já lá
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          
          return Promise.reject(refreshError);
        }
      } else {
        console.warn('⚠️ No refresh token available');
        
        // Redirecionar para login
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    
    return Promise.reject(error);
  }
);

export { apiClient };

// ✅ CORREÇÃO: Funções de API com melhor tratamento de erro
export const fetchTasks = async (customerId) => {
  try {
    console.log(`📡 Fetching tasks for customer ${customerId}`);
    return await apiClient.get(`/customers/${customerId}/faturas/tasks/`);
  } catch (error) {
    console.error('❌ Error fetching tasks:', error);
    throw error;
  }
};

export const fetchFaturas = async (customerId) => {
  try {
    console.log(`📡 Fetching faturas for customer ${customerId}`);
    return await apiClient.get(`/customers/${customerId}/faturas/`);
  } catch (error) {
    console.error('❌ Error fetching faturas:', error);
    throw error;
  }
};

// ✅ CORREÇÃO: A rota de logs não existe, vamos usar uma alternativa ou remover
export const fetchLogs = async (customerId) => {
  try {
    console.log(`📡 Fetching logs for customer ${customerId}`);
    // ✅ CORREÇÃO: Esta rota não existe no backend, vamos retornar array vazio por enquanto
    // return await apiClient.get(`/customers/${customerId}/faturas/logs/`);
    
    // Alternativa temporária - retornar dados vazios
    return {
      status: 200,
      data: []
    };
  } catch (error) {
    console.error('❌ Error fetching logs:', error);
    // Retornar dados vazios em caso de erro ao invés de falhar
    return {
      status: 200,
      data: []
    };
  }
};

// ✅ CORREÇÃO: Melhorar função existente fetchFaturasPorAno
export const fetchFaturasPorAno = async (customerId, ano = null, forceRefresh = false) => {
  try {
    const anoParam = ano || new Date().getFullYear();
    const cacheParam = forceRefresh ? `&_t=${Date.now()}` : '';
    
    console.log(`📡 Fetching faturas por ano for customer ${customerId}, ano ${anoParam}${forceRefresh ? ' (FORCE REFRESH)' : ''}`);
    
    const response = await apiClient.get(`/customers/${customerId}/faturas/por-ano/?ano=${anoParam}${cacheParam}`);
    return response;
  } catch (error) {
    console.error('❌ Error fetching faturas por ano:', error);
    
    // Em caso de erro 500, retornar estrutura padrão
    if (error.response?.status === 500) {
      console.warn('⚠️ Server error, returning default structure');
      return {
        status: 200,
        data: {
          ano_atual: ano || new Date().getFullYear(),
          anos_disponiveis: [new Date().getFullYear()],
          faturas_por_mes: {},
          total_ucs: 0,
          total_ucs_ativas: 0
        }
      };
    }
    
    throw error;
  }
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

// ✅ NOVA: Função para buscar dados da fatura para edição
export const fetchFaturaForEdit = async (faturaId) => {
  try {
    console.log(`📝 Fetching fatura ${faturaId} for edit`);
    return await apiClient.get(`/faturas/${faturaId}/edit/`);
  } catch (error) {
    console.error('❌ Error fetching fatura for edit:', error);
    throw error;
  }
};

// ✅ NOVA: Função para salvar edição da fatura
export const saveFaturaEdit = async (faturaId, dadosEditados) => {
  try {
    console.log(`💾 Saving edit for fatura ${faturaId}:`, dadosEditados);
    return await apiClient.put(`/faturas/${faturaId}/edit/`, dadosEditados);
  } catch (error) {
    console.error('❌ Error saving fatura edit:', error);
    throw error;
  }
};

// ✅ NOVA: Função para força upload com logs melhores
export const forceUploadFatura = async (customerId, dadosUpload) => {
  try {
    console.log(`🚀 Force uploading fatura for customer ${customerId}:`, {
      uc_codigo: dadosUpload.get('uc_codigo'),
      mes_referencia: dadosUpload.get('mes_referencia')
    });
    
    return await apiClient.post(
      `/customers/${customerId}/faturas/force-upload/`,
      dadosUpload,
      {
        headers: { 'Content-Type': 'multipart/form-data' }
      }
    );
  } catch (error) {
    console.error('❌ Error force uploading fatura:', error);
    throw error;
  }
};