// frontend/src/pages/ClientProfile.jsx
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import ClientInfoCard from '../components/ClientInfoCard';
import TabNavigation from '../components/TabNavigation';
import UCTable from '../components/UCTable';
import EmptyState from '../components/EmptyState';
import ActionButton from '../components/ActionButton';
import FaturaImport from '../components/FaturaImport';
import { 
  fetchCustomer as apiFetchCustomer,
  fetchUCs as apiFetchUCs,
  addUC as apiAddUC,
  deleteUC as apiDeleteUC,
  toggleUCStatus as apiToggleUCStatus,
  updateUC as apiUpdateUC 
} from '../services/api';

function ClientProfile() {
  const [client, setClient] = useState(null);
  const { id } = useParams();
  const [activeTab, setActiveTab] = useState('uc');
  const [ucs, setUcs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dataLoaded, setDataLoaded] = useState(false);

  const fetchUCs = async () => {
    try {
      const response = await apiFetchUCs(id);
      if (response.status === 200) {
        setUcs(response.data);
      }
    } catch (error) {
      console.error('Error fetching UCs:', error);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Fetch client data
        const clientResponse = await apiFetchCustomer(id);
        if (clientResponse.status === 200) {
          setClient(clientResponse.data);
        }
        
        // Fetch UCs
        await fetchUCs();
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
        setDataLoaded(true);
      }
    };

    fetchData();
  }, [id]);

  const handleAddUc = async (newUc) => {
    try {
      const response = await apiAddUC(id, newUc);
      
      if (response.status === 201) { // HTTP 201 for created
        setUcs([...ucs, response.data]);
      } else {
        const error = response.data;
        alert('Erro ao adicionar UC: ' + (error.codigo?.[0] || error.detail || 'Erro desconhecido'));
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Erro ao adicionar UC');
    }
  };

  const handleDeleteUc = async (ucId) => {
    if (!confirm('Tem certeza que deseja excluir esta UC?')) return;
    
    try {
      const response = await apiDeleteUC(id, ucId);
      
      if (response.status === 204) { // HTTP 204 for no content
        setUcs(ucs.filter(uc => uc.id !== ucId));
      } else {
        const error = response.data;
        alert('Erro: ' + (error.error || 'Não foi possível excluir a UC'));
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Erro ao excluir UC');
    }
  };

  const handleToggleStatus = async (ucId) => {
    try {
      const response = await apiToggleUCStatus(id, ucId);
      
      if (response.status === 200) {
        const updatedUc = response.data;
        setUcs(ucs.map(uc => uc.id === ucId ? updatedUc : uc));
      } else {
        alert('Erro ao alterar status da UC');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Erro ao alterar status da UC');
    }
  };

  const handleEditUc = async (editedUc) => {
    try {
      const response = await apiUpdateUC(id, editedUc.id, {
        codigo: editedUc.codigo,
        endereco: editedUc.endereco,
        tipo: editedUc.tipo,
        data_vigencia_inicio: editedUc.data_vigencia_inicio,
        data_vigencia_fim: editedUc.data_vigencia_fim,
      });
      
      if (response.status === 200) {
        const updatedUc = response.data;
        setUcs(ucs.map(uc => uc.id === editedUc.id ? updatedUc : uc));
      } else {
        const error = response.data;
        alert('Erro ao editar UC: ' + (error.detail || 'Erro desconhecido'));
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Erro ao editar UC');
    }
  };

  if (loading || !client || !dataLoaded) {
    return (
      <div className="min-h-screen p-4 md:p-8 flex items-center justify-center">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-4xl text-indigo-600 mb-4"></i>
          <p className="text-gray-600">Carregando dados do cliente...</p>
        </div>
      </div>
    );
  }
  return (
    <div className="min-h-screen bg-gray-100 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <Link to="/customer-registration" className="text-indigo-600 hover:text-indigo-800 mb-4 inline-block">
            <i className="fas fa-arrow-left mr-2"></i>
            Voltar para lista de clientes
          </Link>
          <h1 className="text-3xl font-bold text-gray-800">Perfil do Cliente</h1>
        </div>
        
        <ClientInfoCard client={client} onEdit={() => console.log('Edit client')} />
        
        <div className="bg-white rounded-xl shadow-md overflow-hidden mt-6">
          <TabNavigation
            activeTab={activeTab}
            onTabChange={setActiveTab}
            tabs={[
              { id: 'uc', label: 'Unidades Consumidoras', icon: 'plug' },
              { id: 'documents', label: 'Documentos', icon: 'file' },
              { id: 'invoices', label: 'Faturas', icon: 'file-invoice-dollar' },
              { id: 'utility', label: 'Concessionária', icon: 'building' },
              { id: 'history', label: 'Histórico', icon: 'history' }
            ]}
          />
          
          <div className="p-6">
            {activeTab === 'uc' && (
              <UCTable
                ucs={ucs}
                onAddUc={handleAddUc}
                onDeleteUc={handleDeleteUc}
                onToggleStatus={handleToggleStatus}
                onEditUc={handleEditUc}
              />
            )}
            
            {activeTab === 'documents' && (
              <EmptyState
                icon="file-alt"
                title="Documentos do cliente"
                description="Adicione documentos como contratos, faturas e comprovantes nesta seção."
                action={
                  <ActionButton
                    icon="plus"
                    onClick={() => console.log('Add document')}
                  >
                    Adicionar Documento
                  </ActionButton>
                }
              />
            )}
            
            {activeTab === 'invoices' && (
              <EmptyState
                icon="file-invoice-dollar"
                title="Faturas do cliente"
                description="Visualize e gerencie as faturas de energia do cliente."
                action={
                  <ActionButton
                    icon="download"
                    onClick={() => console.log('Import invoices')}
                  >
                    Importar Faturas
                  </ActionButton>
                }
              />
            )}

            {activeTab === 'utility' && (
              <FaturaImport customerId={id} />
            )}
            
            {activeTab === 'history' && (
              <EmptyState
                icon="history"
                title="Histórico do cliente"
                description="Visualize o histórico de consumo, pagamentos e interações com o cliente."
                action={
                  <ActionButton
                    icon="chart-line"
                    onClick={() => console.log('View charts')}
                  >
                    Ver Gráficos
                  </ActionButton>
                }
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ClientProfile;