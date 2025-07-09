// frontend/src/components/Modal.jsx
import React, { useState, useEffect } from 'react';
import { FaTimes, FaSave, FaSpinner, FaEdit, FaFileInvoiceDollar } from 'react-icons/fa';

const FaturaEditModal = ({ fatura, isOpen, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    valor_total: '',
    data_vencimento: '',
    mes_referencia: ''
  });
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState({});

  // Carregar dados da fatura quando o modal abrir
  useEffect(() => {
    if (fatura && isOpen) {
      setFormData({
        valor_total: fatura.valor_total || '',
        data_vencimento: fatura.data_vencimento || '',
        mes_referencia: fatura.mes_referencia || ''
      });
      setErrors({});
    }
  }, [fatura, isOpen]);

  const validateForm = () => {
    const newErrors = {};

    // Validar valor total
    if (formData.valor_total && isNaN(parseFloat(formData.valor_total.replace(',', '.')))) {
      newErrors.valor_total = 'Valor deve ser um número válido';
    }

    // Validar data de vencimento
    if (formData.data_vencimento) {
      const dateRegex = /^\d{2}\/\d{2}\/\d{4}$/;
      if (!dateRegex.test(formData.data_vencimento)) {
        newErrors.data_vencimento = 'Data deve estar no formato DD/MM/AAAA';
      } else {
        // Verificar se a data é válida
        const [day, month, year] = formData.data_vencimento.split('/');
        const date = new Date(year, month - 1, day);
        if (date.getDate() != day || date.getMonth() != month - 1 || date.getFullYear() != year) {
          newErrors.data_vencimento = 'Data inválida';
        }
      }
    }

    // Validar mês de referência
    if (formData.mes_referencia) {
      const mesRegex = /^[A-Z]{3}\/\d{4}$/;
      if (!mesRegex.test(formData.mes_referencia)) {
        newErrors.mes_referencia = 'Mês deve estar no formato MMM/AAAA (ex: JAN/2025)';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Limpar erro do campo quando o usuário começar a digitar
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  const formatCurrency = (value) => {
    // Remove tudo que não for número ou vírgula/ponto
    const cleanValue = value.replace(/[^\d,.-]/g, '');
    return cleanValue;
  };

  const formatDate = (value) => {
    // Remove tudo que não for número
    const cleanValue = value.replace(/\D/g, '');
    
    // Adiciona as barras automaticamente
    if (cleanValue.length >= 5) {
      return `${cleanValue.slice(0, 2)}/${cleanValue.slice(2, 4)}/${cleanValue.slice(4, 8)}`;
    } else if (cleanValue.length >= 3) {
      return `${cleanValue.slice(0, 2)}/${cleanValue.slice(2)}`;
    }
    return cleanValue;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    setIsSaving(true);

    try {
      await onSave(formData);
    } catch (error) {
      console.error('Erro ao salvar:', error);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen || !fatura) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-md m-4 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center">
            <FaFileInvoiceDollar className="h-6 w-6 text-blue-600 mr-3" />
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Editar Fatura
              </h2>
              <p className="text-sm text-gray-500">
                UC: {fatura.unidade_consumidora}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSaving}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <FaTimes className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6">
          {/* Valor Total */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Valor Total (R$)
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                R$
              </span>
              <input
                type="text"
                value={formData.valor_total}
                onChange={(e) => handleInputChange('valor_total', formatCurrency(e.target.value))}
                className={`w-full pl-8 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.valor_total ? 'border-red-300' : 'border-gray-300'
                }`}
                placeholder="0,00"
                disabled={isSaving}
              />
            </div>
            {errors.valor_total && (
              <p className="mt-1 text-sm text-red-600">{errors.valor_total}</p>
            )}
          </div>

          {/* Data de Vencimento */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data de Vencimento
            </label>
            <input
              type="text"
              value={formData.data_vencimento}
              onChange={(e) => handleInputChange('data_vencimento', formatDate(e.target.value))}
              className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.data_vencimento ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="DD/MM/AAAA"
              maxLength="10"
              disabled={isSaving}
            />
            {errors.data_vencimento && (
              <p className="mt-1 text-sm text-red-600">{errors.data_vencimento}</p>
            )}
          </div>

          {/* Mês de Referência */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Mês de Referência
            </label>
            <input
              type="text"
              value={formData.mes_referencia}
              onChange={(e) => handleInputChange('mes_referencia', e.target.value.toUpperCase())}
              className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.mes_referencia ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="JAN/2025"
              maxLength="8"
              disabled={isSaving}
            />
            {errors.mes_referencia && (
              <p className="mt-1 text-sm text-red-600">{errors.mes_referencia}</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Formato: JAN/2025, FEV/2025, etc.
            </p>
          </div>

          {/* Informações adicionais */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Informações da Fatura
            </h4>
            <div className="space-y-1 text-sm text-gray-600">
              <p><strong>ID:</strong> {fatura.id}</p>
              <p><strong>UC:</strong> {fatura.unidade_consumidora}</p>
              {fatura.downloaded_at && (
                <p><strong>Baixada em:</strong> {fatura.downloaded_at}</p>
              )}
              {fatura.arquivo_url && (
                <p>
                  <strong>Arquivo:</strong>{' '}
                  <a 
                    href={fatura.arquivo_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 underline"
                  >
                    Visualizar PDF
                  </a>
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end space-x-3 p-6 border-t bg-gray-50 rounded-b-lg">
          <button
            onClick={onClose}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            Cancelar
          </button>
          
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 flex items-center"
          >
            {isSaving ? (
              <>
                <FaSpinner className="animate-spin h-4 w-4 mr-2" />
                Salvando...
              </>
            ) : (
              <>
                <FaSave className="h-4 w-4 mr-2" />
                Salvar Alterações
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FaturaEditModal;