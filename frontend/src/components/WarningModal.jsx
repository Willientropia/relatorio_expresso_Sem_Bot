// frontend/src/components/WarningModal.jsx - VERSÃO CORRIGIDA
import React from 'react';
import { FaExclamationTriangle, FaTimes, FaUser, FaFileInvoiceDollar, FaPlug } from 'react-icons/fa';

const WarningModal = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  warningType, 
  warningData, 
  isProcessing = false 
}) => {
  if (!isOpen) return null;

  const renderWarningContent = () => {
    switch (warningType) {
      case 'uc_outro_cliente':
        return (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 mb-4">
              <FaExclamationTriangle className="h-6 w-6 text-yellow-600" />
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              UC Pertence a Outro Cliente
            </h3>
            
            <div className="bg-yellow-50 p-4 rounded-lg mb-4">
              <div className="flex items-start">
                <FaUser className="h-5 w-5 text-yellow-600 mt-0.5 mr-3" />
                <div className="text-left">
                  <p className="text-sm text-yellow-800">
                    <span className="font-semibold">UC {warningData?.uc_codigo}</span> está atualmente cadastrada no cliente:
                  </p>
                  <p className="text-sm font-bold text-yellow-900 mt-1">
                    {warningData?.cliente_nome}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="text-sm text-gray-600 mb-6">
              <p>
                Esta unidade consumidora pertence a outro cliente do sistema. 
                Verifique se você selecionou o cliente correto ou se há erro no código da UC.
              </p>
              <p className="mt-2 text-xs text-gray-500">
                💡 Para transferir a UC, use a funcionalidade de transferência no sistema.
              </p>
            </div>
          </div>
        );
        
      case 'uc_nao_encontrada':
        return (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
              <FaPlug className="h-6 w-6 text-red-600" />
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              UC Não Encontrada
            </h3>
            
            <div className="bg-red-50 p-4 rounded-lg mb-4">
              <div className="text-left">
                <p className="text-sm text-red-800">
                  A UC <span className="font-semibold">{warningData?.uc_codigo}</span> não está cadastrada no sistema.
                </p>
                <p className="text-sm text-red-700 mt-2">
                  {warningData?.mensagem}
                </p>
              </div>
            </div>
            
            <div className="text-sm text-gray-600 mb-6">
              <p>
                Antes de enviar esta fatura, você precisa:
              </p>
              <ul className="text-left mt-2 space-y-1 text-xs">
                <li>• Cadastrar a UC {warningData?.uc_codigo} neste cliente</li>
                <li>• Verificar se o código da UC está correto no PDF</li>
                <li>• Confirmar se é o cliente correto para esta fatura</li>
              </ul>
            </div>
          </div>
        );
        
      case 'fatura_duplicada':
        return (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-orange-100 mb-4">
              <FaFileInvoiceDollar className="h-6 w-6 text-orange-600" />
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Fatura Já Existente
            </h3>
            
            <div className="bg-orange-50 p-4 rounded-lg mb-4">
              <div className="text-left">
                <p className="text-sm text-orange-800">
                  Já existe uma fatura para:
                </p>
                <div className="mt-2 space-y-1">
                  <p className="text-sm font-semibold text-orange-900">
                    UC: {warningData?.uc_codigo}
                  </p>
                  <p className="text-sm font-semibold text-orange-900">
                    Período: {warningData?.mes_referencia}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="text-sm text-gray-600 mb-6">
              <p>
                Deseja substituir a fatura existente pela nova?
              </p>
              <p className="mt-2 text-xs text-gray-500">
                ⚠️ A fatura anterior será removida permanentemente.
              </p>
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
                {warningData?.mensagem || 'Verifique os dados e tente novamente.'}
              </p>
            </div>
          </div>
        );
    }
  };

  // Não mostrar botão "Enviar Mesmo Assim" para UCs não encontradas
  const shouldShowConfirmButton = warningType !== 'uc_nao_encontrada' && warningType !== 'uc_outro_cliente';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-md w-full m-4 shadow-xl">
        {/* Header */}
        <div className="flex justify-between items-start p-6 pb-4">
          <div className="flex-1">
            {renderWarningContent()}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
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
            {shouldShowConfirmButton ? 'Cancelar' : 'Entendi'}
          </button>
          
          {shouldShowConfirmButton && (
            <button
              onClick={onConfirm}
              disabled={isProcessing}
              className="px-4 py-2 text-sm font-medium text-white bg-yellow-600 border border-transparent rounded-md hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:opacity-50 flex items-center"
            >
              {isProcessing ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Enviando...
                </>
              ) : (
                'Substituir Fatura'
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default WarningModal;