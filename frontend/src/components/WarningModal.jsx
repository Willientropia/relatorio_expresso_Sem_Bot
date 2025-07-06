// frontend/src/components/WarningModal.jsx - VERSÃO APRIMORADA
import React from 'react';
import { FaExclamationTriangle, FaTimes, FaUser, FaFileInvoiceDollar, FaExchangeAlt, FaBuilding } from 'react-icons/fa';

const WarningModal = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  warningType, 
  warningData, 
  isProcessing = false 
}) => {
  // ✅ DEBUG: Log dos props recebidos
  console.log('🔍 WarningModal props:', { 
    isOpen, 
    warningType, 
    warningData: warningData ? 'presente' : 'ausente', 
    isProcessing 
  });

  if (!isOpen) return null;

  const renderWarningContent = () => {
    switch (warningType) {
      case 'uc_outro_cliente':
        return (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-orange-100 mb-4">
              <FaExchangeAlt className="h-6 w-6 text-orange-600" />
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              UC Pertence a Outro Cliente
            </h3>
            
            <div className="bg-orange-50 p-4 rounded-lg mb-4">
              <div className="text-left space-y-2">
                <div className="flex items-start">
                  <FaBuilding className="h-5 w-5 text-orange-600 mt-0.5 mr-3" />
                  <div>
                    <p className="text-sm text-orange-800">
                      <span className="font-semibold">UC {warningData?.uc_codigo}</span> atualmente pertence a:
                    </p>
                    <p className="text-sm font-bold text-orange-900 mt-1">
                      {warningData?.cliente_atual}
                    </p>
                  </div>
                </div>
                
                <div className="border-l-2 border-orange-300 pl-4 ml-7">
                  <p className="text-xs text-orange-700">
                    <strong>Tentativa de upload:</strong> {warningData?.cliente_tentativa}
                  </p>
                  <p className="text-xs text-orange-700">
                    <strong>Arquivo:</strong> {warningData?.arquivo}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="text-sm text-gray-600 mb-6">
              <p className="mb-2">
                <strong>O que acontecerá se confirmar:</strong>
              </p>
              <ul className="text-left space-y-1 text-xs bg-gray-50 p-3 rounded">
                <li>• A UC será transferida para o cliente atual ({warningData?.cliente_tentativa})</li>
                <li>• A fatura será vinculada ao novo titular</li>
                <li>• O histórico de titularidade será preservado</li>
              </ul>
              
              <p className="mt-3 text-xs text-gray-500">
                ⚠️ Esta ação pode indicar uma transferência de titularidade ou erro de dados.
              </p>
            </div>
          </div>
        );
        
      case 'fatura_duplicada':
        return (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 mb-4">
              <FaFileInvoiceDollar className="h-6 w-6 text-yellow-600" />
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Fatura Já Existente
            </h3>
            
            <div className="bg-yellow-50 p-4 rounded-lg mb-4">
              <div className="text-left">
                <p className="text-sm text-yellow-800 mb-3">
                  Já existe uma fatura para este período:
                </p>
                
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-yellow-900">UC:</span>
                    <span className="text-sm text-yellow-800">{warningData?.uc_codigo}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-yellow-900">Período:</span>
                    <span className="text-sm text-yellow-800">{warningData?.mes_referencia_texto || warningData?.mes_referencia}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-yellow-900">Cliente:</span>
                    <span className="text-sm text-yellow-800">{warningData?.cliente_nome}</span>
                  </div>
                  {warningData?.fatura_existente_valor && (
                    <div className="flex justify-between">
                      <span className="text-sm font-medium text-yellow-900">Valor atual:</span>
                      <span className="text-sm text-yellow-800">R$ {warningData.fatura_existente_valor}</span>
                    </div>
                  )}
                </div>
                
                <div className="mt-3 pt-3 border-t border-yellow-200">
                  <p className="text-xs text-yellow-700">
                    <strong>Novo arquivo:</strong> {warningData?.arquivo}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="text-sm text-gray-600 mb-6">
              <p className="mb-2">
                <strong>O que acontecerá se confirmar:</strong>
              </p>
              <ul className="text-left space-y-1 text-xs bg-gray-50 p-3 rounded">
                <li>• A fatura existente será substituída</li>
                <li>• O arquivo anterior será removido permanentemente</li>
                <li>• Os novos dados extraídos serão salvos</li>
              </ul>
              
              <p className="mt-3 text-xs text-red-600">
                ⚠️ Esta ação não pode ser desfeita.
              </p>
            </div>
          </div>
        );
        
      case 'multiplos_avisos':
        return (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-purple-100 mb-4">
              <FaExclamationTriangle className="h-6 w-6 text-purple-600" />
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Múltiplos Conflitos Detectados
            </h3>
            
            <div className="bg-purple-50 p-4 rounded-lg mb-4 max-h-60 overflow-y-auto">
              <div className="text-left space-y-3">
                <p className="text-sm text-purple-800 font-medium mb-3">
                  Foram detectados {warningData?.total_avisos || 'vários'} conflitos:
                </p>
                
                {warningData?.avisos_resumo?.map((aviso, index) => (
                  <div key={index} className="bg-white p-2 rounded border border-purple-200">
                    <div className="flex items-center mb-1">
                      {aviso.tipo === 'uc_outro_cliente' ? (
                        <FaExchangeAlt className="h-4 w-4 text-orange-500 mr-2" />
                      ) : (
                        <FaFileInvoiceDollar className="h-4 w-4 text-yellow-500 mr-2" />
                      )}
                      <span className="text-xs font-medium text-gray-800">
                        {aviso.tipo === 'uc_outro_cliente' ? 'UC de outro cliente' : 'Fatura duplicada'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">
                      UC {aviso.uc_codigo} - {aviso.arquivo}
                    </p>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="text-sm text-gray-600 mb-6">
              <p>
                Todos os conflitos serão resolvidos conforme as regras padrão:
              </p>
              <ul className="text-left space-y-1 text-xs bg-gray-50 p-3 rounded mt-2">
                <li>• UCs serão transferidas quando necessário</li>
                <li>• Faturas duplicadas serão substituídas</li>
                <li>• Histórico será preservado</li>
              </ul>
            </div>
          </div>
        );
        
      default:
        return (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
              <FaExclamationTriangle className="h-6 w-6 text-red-600" />
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Aviso de Validação
            </h3>
            
            <div className="text-sm text-gray-600 mb-6">
              <p>Foi detectado um problema na validação dos dados.</p>
              <p className="mt-2 text-xs text-gray-500">
                Tipo: {warningType || 'Desconhecido'}
              </p>
            </div>
          </div>
        );
    }
  };

  // Determinar texto do botão baseado no tipo de aviso
  const getConfirmButtonText = () => {
    if (isProcessing) {
      return 'Processando...';
    }
    
    switch (warningType) {
      case 'uc_outro_cliente':
        return 'Transferir UC e Enviar';
      case 'fatura_duplicada':
        return 'Substituir Fatura';
      case 'multiplos_avisos':
        return 'Resolver Todos os Conflitos';
      default:
        return 'Confirmar';
    }
  };

  // Determinar cor do botão baseado no tipo de aviso
  const getConfirmButtonClass = () => {
    const baseClass = "px-4 py-2 text-sm font-medium text-white border border-transparent rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 flex items-center";
    
    switch (warningType) {
      case 'uc_outro_cliente':
        return `${baseClass} bg-orange-600 hover:bg-orange-700 focus:ring-orange-500`;
      case 'fatura_duplicada':
        return `${baseClass} bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500`;
      case 'multiplos_avisos':
        return `${baseClass} bg-purple-600 hover:bg-purple-700 focus:ring-purple-500`;
      default:
        return `${baseClass} bg-red-600 hover:bg-red-700 focus:ring-red-500`;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-md w-full m-4 shadow-xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-start p-6 pb-4">
          <div className="flex-1">
            {renderWarningContent()}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors ml-4"
            disabled={isProcessing}
          >
            <FaTimes className="h-5 w-5" />
          </button>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 rounded-b-lg flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={isProcessing}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            Cancelar
          </button>
          
          <button
            onClick={onConfirm}
            disabled={isProcessing}
            className={getConfirmButtonClass()}
          >
            {isProcessing ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {getConfirmButtonText()}
              </>
            ) : (
              getConfirmButtonText()
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default WarningModal;