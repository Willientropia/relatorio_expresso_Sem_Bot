// frontend/src/components/FaturaImport.jsx - VERSÃO CORRIGIDA
import { useState, useEffect } from 'react';
import ActionButton from './ActionButton';
import EmptyState from './EmptyState';
import { 
  fetchTasks as apiFetchTasks, 
  fetchFaturas as apiFetchFaturas, 
  startImport as apiStartImport,
  apiClient 
} from '../services/api';
import FaturaUpload from './FaturaUpload';

const FaturaImport = ({ customerId }) => {
  const [tasks, setTasks] = useState([]);
  const [faturasPorAno, setFaturasPorAno] = useState({});
  const [logs, setLogs] = useState([]); // Manter por compatibilidade
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [activeTab, setActiveTab] = useState('faturas');
  const [anoSelecionado, setAnoSelecionado] = useState(new Date().getFullYear());
  const [anosDisponiveis, setAnosDisponiveis] = useState([]);

  // ✅ CORREÇÃO: Buscar faturas organizadas por ano
  const fetchFaturasPorAno = async (ano = null) => {
    try {
      const anoParam = ano || anoSelecionado;
      console.log(`📡 Buscando faturas para ano ${anoParam}, cliente ${customerId}`);
      
      const response = await apiClient.get(`/customers/${customerId}/faturas/por-ano/?ano=${anoParam}`);
      
      if (response.status === 200 && response.data) {
        console.log('✅ Dados recebidos:', response.data);
        setFaturasPorAno(response.data.faturas_por_mes || {});
        setAnosDisponiveis(response.data.anos_disponiveis || [anoParam]);
        setAnoSelecionado(response.data.ano_atual || anoParam);
      }
    } catch (error) {
      console.error('❌ Erro ao buscar faturas por ano:', error);
      
      // ✅ CORREÇÃO: Em caso de erro, definir estrutura padrão
      const currentYear = ano || anoSelecionado;
      setFaturasPorAno({});
      setAnosDisponiveis([currentYear]);
      setAnoSelecionado(currentYear);
      
      // Mostrar erro específico se for 500
      if (error.response?.status === 500) {
        console.error('🚨 Erro interno do servidor. Verifique o backend.');
      }
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await apiFetchTasks(customerId);
      if (response.status === 200) {
        setTasks(response.data);
        
        const hasActiveTask = response.data.some(task => 
          task.status === 'pending' || task.status === 'processing'
        );
        setImporting(hasActiveTask);
      }
    } catch (error) {
      console.error('❌ Erro ao buscar tarefas:', error);
      setTasks([]);
    }
  };

  // ✅ CORREÇÃO: Remover busca de logs por enquanto
  const fetchLogs = async () => {
    try {
      // Por enquanto, deixar vazio até implementarmos os logs no backend
      setLogs([]);
    } catch (error) {
      console.error('❌ Erro ao buscar logs:', error);
      setLogs([]);
    }
  };

  const handleUploadSuccess = () => {
    fetchFaturasPorAno();
  };

  useEffect(() => {
    console.log(`🔄 FaturaImport useEffect executado para cliente ${customerId}`);
    
    fetchTasks();
    fetchFaturasPorAno();
    fetchLogs();

    const interval = setInterval(() => {
      if (importing) {
        fetchTasks();
        fetchFaturasPorAno();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [customerId, importing]);

  const handleStartImport = async () => {
    setLoading(true);
    try {
      const response = await apiStartImport(customerId);
      
      if (response.status === 200) {
        alert('Importação iniciada com sucesso!');
        setImporting(true);
        fetchTasks();
      } else {
        const error = response.data;
        alert(`Erro: ${error.error || 'Não foi possível iniciar a importação'}`);
      }
    } catch (error) {
      console.error('Erro ao iniciar importação:', error);
      alert('Erro ao iniciar importação');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'pending':
        return 'Pendente';
      case 'processing':
        return 'Processando';
      case 'completed':
        return 'Concluída';
      case 'failed':
        return 'Falhou';
      default:
        return status;
    }
  };

  const renderCardUC = (ucInfo, mesNome) => {
    const temFatura = !!ucInfo.fatura;
    
    return (
      <div 
        key={ucInfo.uc_id} 
        className={`p-3 rounded-lg border-2 transition-all duration-200 ${
          temFatura 
            ? 'bg-green-50 border-green-200 hover:bg-green-100 hover:border-green-300' 
            : 'bg-red-50 border-red-200 hover:bg-red-100 hover:border-red-300'
        }`}
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center">
            <div className={`w-2 h-2 rounded-full mr-2 ${
              temFatura ? 'bg-green-500' : 'bg-red-500'
            }`}></div>
            <span className="font-semibold text-gray-800 text-sm">
              UC: {ucInfo.uc_codigo}
            </span>
          </div>
          <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {ucInfo.uc_tipo}
          </div>
        </div>
        
        <div className="text-xs text-gray-600 mb-3 truncate" title={ucInfo.uc_endereco}>
          {ucInfo.uc_endereco}
        </div>
        
        {temFatura ? (
          <div className="space-y-2">
            {ucInfo.fatura.valor && (
              <div className="text-sm">
                <span className="text-gray-600">Valor: </span>
                <span className="font-medium text-green-600">
                  R$ {ucInfo.fatura.valor}
                </span>
              </div>
            )}
            
            {ucInfo.fatura.vencimento && (
              <div className="text-sm">
                <span className="text-gray-600">Vencimento: </span>
                <span className="font-medium">
                  {ucInfo.fatura.vencimento}
                </span>
              </div>
            )}
            
            <div className="flex justify-between items-center mt-3 pt-2 border-t border-green-200">
              <span className="text-xs text-gray-500">
                Baixada em {ucInfo.fatura.downloaded_at}
              </span>
              {ucInfo.fatura.arquivo_url && (
                <a
                  href={ucInfo.fatura.arquivo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600 transition-colors flex items-center"
                >
                  <i className="fas fa-download mr-1"></i>
                  PDF
                </a>
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <i className="fas fa-exclamation-triangle text-red-400 mb-2"></i>
            <div className="text-sm text-red-600 font-medium">
              Fatura não baixada
            </div>
            <div className="text-xs text-red-500 mt-1">
              {mesNome} de {anoSelecionado}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderFaturasPorMes = () => {
    // ✅ CORREÇÃO: Verificar se há dados válidos
    const hasFaturas = faturasPorAno && Object.keys(faturasPorAno).length > 0;
    
    if (!hasFaturas) {
      return (
        <div>
          <div className="mb-8">
            <FaturaUpload clienteId={customerId} onUploadSuccess={handleUploadSuccess} />
          </div>
          <EmptyState
            icon="calendar-alt"
            title="Nenhuma fatura encontrada"
            description={`As faturas aparecerão organizadas por mês após a importação ou envio manual para o ano de ${anoSelecionado}.`}
          />
        </div>
      );
    }

    return (
      <div>
        {/* Seletor de Ano */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-semibold text-gray-800">
              Faturas de {anoSelecionado}
            </h3>
            <select
              value={anoSelecionado}
              onChange={(e) => {
                const novoAno = parseInt(e.target.value);
                setAnoSelecionado(novoAno);
                fetchFaturasPorAno(novoAno);
              }}
              className="px-3 py-1 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
            >
              {anosDisponiveis.map(ano => (
                <option key={ano} value={ano}>{ano}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Upload Component */}
        <div className="mb-8">
          <FaturaUpload clienteId={customerId} onUploadSuccess={handleUploadSuccess} />
        </div>
        
        {/* Grade de Meses */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Object.values(faturasPorAno).map((mesData) => {
            // Filtrar apenas UCs ativas
            const ucsAtivas = mesData.ucs?.filter(uc => uc.uc_is_active) || [];
            const totalUCs = ucsAtivas.length;
            const ucsComFatura = ucsAtivas.filter(uc => uc.fatura).length;
            const percentualCompleto = totalUCs > 0 ? (ucsComFatura / totalUCs) * 100 : 0;
            
            // Determinar cor do header baseado na completude
            let headerColor = 'bg-red-500'; // Nenhuma fatura
            if (percentualCompleto === 100) {
              headerColor = 'bg-green-500'; // Todas as faturas
            } else if (percentualCompleto > 0) {
              headerColor = 'bg-yellow-500'; // Algumas faturas
            }
            
            return (
              <div key={mesData.mes_numero} className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow">
                {/* Header do Mês */}
                <div className={`p-4 ${headerColor} text-white`}>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-lg font-semibold">
                      {mesData.mes_nome}
                    </h4>
                    <div className="text-sm font-medium">
                      {ucsComFatura}/{totalUCs}
                    </div>
                  </div>
                  
                  {/* Barra de Progresso */}
                  <div className="bg-white bg-opacity-30 rounded-full h-2 mb-2">
                    <div 
                      className="bg-white h-2 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${percentualCompleto}%` }}
                    ></div>
                  </div>
                  
                  <div className="text-xs opacity-90">
                    {percentualCompleto.toFixed(0)}% completo
                  </div>
                </div>
                
                {/* UCs do Mês */}
                <div className="p-4">
                  {totalUCs === 0 ? (
                    <div className="text-center py-6 text-gray-500">
                      <i className="fas fa-inbox text-2xl mb-2 text-gray-300"></i>
                      <div className="text-sm">Nenhuma UC ativa</div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {ucsAtivas.map(ucInfo => 
                        renderCardUC(ucInfo, mesData.mes_nome)
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderTasks = () => {
    if (tasks.length === 0) {
      return (
        <EmptyState
          icon="tasks"
          title="Nenhuma tarefa de importação"
          description="Clique em 'Importar Faturas em aberto' para iniciar"
        />
      );
    }

    return (
      <div className="space-y-4">
        {tasks.map((task) => (
          <div key={task.id} className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900">
                  UC: {task.unidade_consumidora_codigo}
                </h4>
                <p className="text-sm text-gray-500">
                  Criada em: {new Date(task.created_at).toLocaleString('pt-BR')}
                </p>
                {task.error_message && (
                  <p className="text-sm text-red-600 mt-1">
                    Erro: {task.error_message}
                  </p>
                )}
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(task.status)}`}>
                {getStatusText(task.status)}
              </span>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderLogs = () => {
    if (logs.length === 0) {
      return (
        <EmptyState
          icon="history"
          title="Nenhum log disponível"
          description="Os logs de atividade aparecerão aqui conforme as operações são realizadas"
        />
      );
    }

    return (
      <div className="space-y-4">
        {logs.map((log) => (
          <div key={log.id} className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="mb-2">
              <span className="text-sm text-gray-500">
                {new Date(log.created_at).toLocaleString('pt-BR')}
              </span>
              <p className="font-medium text-gray-900">
                {log.message || 'Log de atividade'}
              </p>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div>
      {/* Debug Info */}
      <div className="mb-4 p-3 bg-gray-100 rounded-lg text-sm text-gray-600">
        <strong>Debug Info:</strong> Cliente ID: {customerId}, Ano: {anoSelecionado}, 
        Anos Disponíveis: {anosDisponiveis.join(', ')}, 
        Faturas Carregadas: {Object.keys(faturasPorAno).length} meses
      </div>

      {/* Botão de importar */}
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">
          Gerenciamento de Faturas
        </h3>
        <ActionButton
          icon="file-import"
          onClick={handleStartImport}
          disabled={loading || importing}
        >
          {importing ? 'Importação em andamento...' : 'Importar Faturas em aberto'}
        </ActionButton>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-4">
        <nav className="flex -mb-px">
          <button
            onClick={() => setActiveTab('faturas')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'faturas'
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <i className="fas fa-calendar-alt mr-1"></i>
            Faturas por Mês
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'tasks'
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <i className="fas fa-tasks mr-1"></i>
            Tarefas ({tasks.length})
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'logs'
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <i className="fas fa-history mr-1"></i>
            Logs ({logs.length})
          </button>
        </nav>
      </div>

      {/* Conteúdo */}
      <div className="mt-4">
        {activeTab === 'faturas' && renderFaturasPorMes()}
        {activeTab === 'tasks' && renderTasks()}
        {activeTab === 'logs' && renderLogs()}
      </div>
    </div>
  );
};

export default FaturaImport;