import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 segundos para análises que podem demorar
});

// Interceptor para tratar erros globalmente
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Erro na API:', error);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Análise de recursos
  analyzeAppeal: async (queryData) => {
    const response = await api.post('/analyze-appeal', queryData);
    return response.data;
  },

  // Análise de recursos com minuta
  analyzeAppealWithDraft: async (queryData) => {
    const response = await api.post('/analyze-appeal-with-draft', queryData);
    return response.data;
  },

  // Busca por protocolo
  findSimilarRequests: async (protocolId, topK = 5) => {
    const response = await api.get(`/context-by-protocol/${protocolId}?top_k=${topK}`);
    return response.data;
  },

  // Busca por ID de recurso
  findSimilarAppeals: async (appealId, topK = 5) => {
    const response = await api.get(`/similar-appeals/${appealId}?top_k=${topK}`);
    return response.data;
  },

  // Obter instâncias disponíveis
  getInstances: async () => {
    const response = await api.get('/instances');
    return response.data.instances;
  },

  // Verificar status da aplicação
  getHealthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Verificar status da geração de minutas
  getMinutaStatus: async () => {
    const response = await api.get('/minuta-status');
    return response.data;
  },

  // Informações básicas da aplicação
  getAppInfo: async () => {
    const response = await api.get('/');
    return response.data;
  },

  // Download de minuta
  downloadMinuta: async (minutaData) => {
    const response = await api.post('/download-minuta', minutaData, {
      responseType: 'blob'
    });
    return response;
  }
};

export default api;