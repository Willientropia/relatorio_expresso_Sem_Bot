// frontend/src/components/DebugPanel.jsx
import React, { useState } from 'react';
import { apiClient } from '../services/api';

const DebugPanel = ({ customerId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [debugInfo, setDebugInfo] = useState('');
  const [loading, setLoading] = useState(false);

  const testForceUpload = async () => {
    setLoading(true);
    setDebugInfo('Testando force upload...\n');
    
    try {
      // Simular um upload com dados de teste
      const formData = new FormData();
      
      // Criar um arquivo de teste
      const testFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      formData.append('arquivo', testFile);
      formData.append('uc_codigo', '1340008741');
      formData.append('mes_referencia', '03/2025');
      formData.append('dados_extraidos', JSON.stringify({
        valor_total: '10.00',
        data_vencimento: '20/04/2025',
        unidade_consumidora: '1340008741',
        mes_referencia: 'MAR/2025'
      }));

      const response = await apiClient.post(
        `/customers/${customerId}/faturas/force-upload/`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      setDebugInfo(prev => prev + `✅ Sucesso: ${JSON.stringify(response.data, null, 2)}\n`);
    } catch (error) {
      setDebugInfo(prev => prev + `❌ Erro: ${error.response?.data?.error || error.message}\n`);
      console.error('Debug error:', error);
    } finally {
      setLoading(false);
    }
  };

  const testFaturasList = async () => {
    setLoading(true);
    setDebugInfo('Testando listagem de faturas...\n');
    
    try {
      const response = await apiClient.get(`/customers/${customerId}/faturas/por-ano/?ano=2025&_t=${Date.now()}`);
      setDebugInfo(prev => prev + `✅ Faturas encontradas: ${JSON.stringify(response.data, null, 2)}\n`);
    } catch (error) {
      setDebugInfo(prev => prev + `❌ Erro ao buscar faturas: ${error.response?.data?.error || error.message}\n`);
      console.error('Debug error:', error);
    } finally {
      setLoading(false);
    }
  };

  const testEditFatura = async () => {
    setLoading(true);
    setDebugInfo('Testando edição de fatura...\n');
    
    try {
      // Primeiro, buscar uma fatura existente
      const listResponse = await apiClient.get(`/customers/${customerId}/faturas/por-ano/?ano=2025`);
      
      // Encontrar uma fatura para testar
      let faturaId = null;
      const faturasPorMes = listResponse.data.faturas_por_mes || {};
      
      for (const mesData of Object.values(faturasPorMes)) {
        for (const uc of mesData.ucs || []) {
          if (uc.fatura) {
            faturaId = uc.fatura.id;
            break;
          }
        }
        if (faturaId) break;
      }

      if (faturaId) {
        setDebugInfo(prev => prev + `📝 Testando edição da fatura ${faturaId}...\n`);
        
        // Buscar dados da fatura
        const getResponse = await apiClient.get(`/faturas/${faturaId}/edit/`);
        setDebugInfo(prev => prev + `✅ Dados da fatura: ${JSON.stringify(getResponse.data, null, 2)}\n`);
        
        // Testar atualização
        const updateResponse = await apiClient.put(`/faturas/${faturaId}/edit/`, {
          valor_total: '15.50',
          data_vencimento: '25/04/2025'
        });
        setDebugInfo(prev => prev + `✅ Fatura atualizada: ${JSON.stringify(updateResponse.data, null, 2)}\n`);
      } else {
        setDebugInfo(prev => prev + `⚠️ Nenhuma fatura encontrada para testar edição\n`);
      }
    } catch (error) {
      setDebugInfo(prev => prev + `❌ Erro na edição: ${error.response?.data?.error || error.message}\n`);
      console.error('Debug error:', error);
    } finally {
      setLoading(false);
    }
  };

  const clearDebug = () => {
    setDebugInfo('');
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 bg-red-600 text-white p-3 rounded-full shadow-lg hover:bg-red-700 z-50"
        title="Abrir painel de debug"
      >
        🐛
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-white border border-gray-300 rounded-lg shadow-xl z-50">
      {/* Header */}
      <div className="flex justify-between items-center p-4 border-b bg-red-50">
        <h3 className="font-semibold text-red-800">🐛 Debug Panel</h3>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="space-y-2 mb-4">
          <button
            onClick={testFaturasList}
            disabled={loading}
            className="w-full px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 text-sm"
          >
            🔍 Testar Listagem de Faturas
          </button>
          
          <button
            onClick={testForceUpload}
            disabled={loading}
            className="w-full px-3 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:opacity-50 text-sm"
          >
            🚀 Testar Force Upload
          </button>
          
          <button
            onClick={testEditFatura}
            disabled={loading}
            className="w-full px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 text-sm"
          >
            ✏️ Testar Edição de Fatura
          </button>
          
          <button
            onClick={clearDebug}
            disabled={loading}
            className="w-full px-3 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50 text-sm"
          >
            🗑️ Limpar Log
          </button>
        </div>

        {/* Debug Output */}
        <div className="bg-black text-green-400 p-3 rounded text-xs h-64 overflow-y-auto font-mono">
          {loading && <div className="text-yellow-400">⏳ Executando...</div>}
          <pre className="whitespace-pre-wrap">{debugInfo || 'Nenhum debug executado ainda.'}</pre>
        </div>
      </div>

      {/* Footer */}
      <div className="p-2 border-t bg-gray-50 text-xs text-gray-600">
        Cliente ID: {customerId}
      </div>
    </div>
  );
};

export default DebugPanel;