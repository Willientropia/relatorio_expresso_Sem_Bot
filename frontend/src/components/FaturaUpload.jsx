// frontend/src/components/FaturaUpload.jsx - VERSÃO CORRIGIDA COMPLETA

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { FaUpload, FaFilePdf, FaSpinner, FaTimes, FaEdit, FaSave, FaEye } from 'react-icons/fa';
import { apiClient } from '../services/api';
import WarningModal from './WarningModal';

const FaturaUpload = ({ clienteId, onUploadSuccess }) => {
  const [documents, setDocuments] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);
  const [warningModal, setWarningModal] = useState({
    isOpen: false,
    type: null,
    data: null,
    pendingUploads: [] // ✅ CORREÇÃO: Suportar múltiplos avisos
  });
  const fileInputRef = useRef(null);

  // ✅ DEBUG: Monitorar mudanças no warningModal
  useEffect(() => {
    console.log('🔍 WarningModal state changed:', warningModal);
  }, [warningModal]);

  // Função de extração integrada com o backend
  const extractInvoiceData = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiClient.post('/faturas/extract_data/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Erro ao extrair dados da fatura:', error);
      throw error;
    }
  };

  const handleFilesDrop = useCallback(async (files) => {
    const fileArray = Array.from(files).filter(file => file.type === 'application/pdf');
    
    if (fileArray.length === 0) {
      alert('Por favor, selecione apenas arquivos PDF');
      return;
    }

    setIsProcessing(true);
    
    const newDocuments = [];
    
    for (const file of fileArray) {
      const id = `doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const fileUrl = URL.createObjectURL(file);
      
      try {
        const extractedData = await extractInvoiceData(file);
        
        newDocuments.push({
          id,
          file,
          fileUrl,
          fileName: file.name,
          extractedData,
          modifiedData: { ...extractedData },
          status: 'reviewed'
        });
      } catch (error) {
        newDocuments.push({
          id,
          file,
          fileUrl,
          fileName: file.name,
          extractedData: null,
          modifiedData: null,
          status: 'error',
          error: 'Erro ao extrair dados da fatura'
        });
      }
    }
    
    setDocuments(newDocuments);
    setActiveTab(0);
    setShowReviewModal(true);
    setIsProcessing(false);
  }, []);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    
    const files = e.dataTransfer.files;
    handleFilesDrop(files);
  };

  const handleFileSelect = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFilesDrop(files);
    }
  };

  const updateDocumentData = (documentId, field, value) => {
    setDocuments(prev => prev.map(doc => 
      doc.id === documentId 
        ? { ...doc, modifiedData: { ...doc.modifiedData, [field]: value } }
        : doc
    ));
  };

  const removeDocument = (documentId) => {
    setDocuments(prev => {
      const newDocs = prev.filter(doc => doc.id !== documentId);
      if (newDocs.length === 0) {
        setShowReviewModal(false);
      } else if (activeTab >= newDocs.length) {
        setActiveTab(newDocs.length - 1);
      }
      return newDocs;
    });
  };

  // ✅ CORREÇÃO: Função para processar avisos em lote
  const processarAvisos = (avisos, faturas_processadas) => {
    console.log('🔍 Processando avisos:', avisos);
    
    if (!avisos || avisos.length === 0) {
      console.log('❌ Nenhum aviso para processar');
      return null;
    }
    
    // Pegar o primeiro aviso para mostrar no modal
    const primeiroAviso = avisos[0];
    console.log('📋 Primeiro aviso:', primeiroAviso);
    
    // Encontrar documento correspondente
    const docCorrespondente = documents.find(doc => 
      doc.fileName === primeiroAviso.arquivo
    );
    
    console.log('📄 Documento correspondente:', docCorrespondente?.fileName);
    
    if (!docCorrespondente) {
      console.error('❌ Documento correspondente não encontrado para aviso:', primeiroAviso);
      console.log('📋 Documentos disponíveis:', documents.map(d => d.fileName));
      return null;
    }
    
    // Preparar dados para o modal baseado no tipo de aviso
    let warningData = {
      type: primeiroAviso.tipo,
      data: primeiroAviso,
      pendingUploads: avisos.map(aviso => {
        const doc = documents.find(d => d.fileName === aviso.arquivo);
        return {
          file: doc?.file,
          uc_codigo: aviso.uc_codigo,
          mes_referencia: aviso.mes_referencia || getMesReferenciaFromDoc(doc),
          dados_extraidos: doc?.extractedData || {},
          aviso_original: aviso
        };
      })
    };
    
    console.log('✅ Warning data preparado:', warningData);
    return warningData;
  };
  
  const getMesReferenciaFromDoc = (doc) => {
    if (!doc?.extractedData?.mes_referencia) return null;
    
    // Converter JAN/2025 para 01/2025
    const mesRef = doc.extractedData.mes_referencia;
    const mesesMap = {
      'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
      'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
      'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
    };
    
    if (mesRef && mesRef.includes('/')) {
      const [mes, ano] = mesRef.split('/');
      const mesNum = mesesMap[mes.toUpperCase()];
      return mesNum ? `${mesNum}/${ano}` : mesRef;
    }
    
    return mesRef;
  };

  // ✅ CORREÇÃO: Função para confirmar avisos
  const handleWarningConfirm = async () => {
    const { pendingUploads } = warningModal;
    if (!pendingUploads || pendingUploads.length === 0) return;

    setWarningModal(prev => ({ ...prev, isProcessing: true }));

    try {
      // Processar todos os uploads pendentes
      const resultados = [];
      
      for (const upload of pendingUploads) {
        try {
          const formData = new FormData();
          formData.append('arquivo', upload.file);
          formData.append('uc_codigo', upload.uc_codigo);
          formData.append('mes_referencia', upload.mes_referencia);
          formData.append('dados_extraidos', JSON.stringify(upload.dados_extraidos));

          const response = await apiClient.post(
            `/customers/${clienteId}/faturas/force-upload/`,
            formData,
            {
              headers: { 'Content-Type': 'multipart/form-data' }
            }
          );

          if (response.status === 201) {
            resultados.push({
              sucesso: true,
              arquivo: upload.file.name,
              resultado: response.data
            });
          }
        } catch (error) {
          resultados.push({
            sucesso: false,
            arquivo: upload.file.name,
            erro: error.response?.data?.error || error.message
          });
        }
      }
      
      // Verificar resultados
      const sucessos = resultados.filter(r => r.sucesso);
      const erros = resultados.filter(r => !r.sucesso);
      
      // Limpar estado
      documents.forEach(doc => {
        if (doc.fileUrl) {
          URL.revokeObjectURL(doc.fileUrl);
        }
      });
      
      setDocuments([]);
      setShowReviewModal(false);
      setWarningModal({
        isOpen: false,
        type: null,
        data: null,
        pendingUploads: []
      });
      
      if (onUploadSuccess) {
        onUploadSuccess();
      }
      
      // Mostrar resultado
      let mensagem = `${sucessos.length} fatura(s) enviada(s) com sucesso!`;
      
      if (erros.length > 0) {
        mensagem += `\n\n${erros.length} erro(s):\n${erros.map(e => `- ${e.arquivo}: ${e.erro}`).join('\n')}`;
      }
      
      alert(mensagem);
      
    } catch (error) {
      console.error('Erro ao forçar upload:', error);
      alert('Erro geral ao processar uploads: ' + (error.response?.data?.error || error.message));
    } finally {
      setWarningModal(prev => ({ ...prev, isProcessing: false }));
    }
  };

  const saveAllDocuments = async () => {
    const validDocuments = documents.filter(doc => doc.status === 'reviewed');
    
    if (validDocuments.length === 0) {
      alert('Nenhum documento válido para salvar');
      return;
    }

    setIsProcessing(true);
    
    try {
      const formData = new FormData();
      
      validDocuments.forEach(doc => {
        formData.append('faturas', doc.file);
      });
      
      console.log(`📤 Enviando ${validDocuments.length} faturas para processamento`);
      
      const response = await apiClient.post(
        `/customers/${clienteId}/faturas/upload-with-extraction/`, 
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      
      console.log('📥 Resposta recebida:', response.status, response.data);
      
      const result = response.data;
      
      // ✅ CORREÇÃO: Debug detalhado da resposta
      console.log('🔍 Detalhes da resposta:', {
        status: response.status,
        temAvisos: result.avisos?.length > 0,
        avisos: result.avisos,
        faturas: result.faturas_processadas?.length || 0,
        erros: result.faturas_com_erro?.length || 0
      });
      
      // ✅ CORREÇÃO: Verificar status da resposta para identificar avisos
      if (response.status === 409 && result.avisos && result.avisos.length > 0) {
        console.log('⚠️ Avisos detectados (status 409):', result.avisos);
        
        const warningData = processarAvisos(result.avisos, result.faturas_processadas);
        
        if (warningData) {
          console.log('✅ Abrindo modal de aviso:', warningData);
          setWarningModal({
            isOpen: true,
            type: warningData.type,
            data: warningData.data,
            pendingUploads: warningData.pendingUploads,
            isProcessing: false
          });
          
          setIsProcessing(false);
          return;
        } else {
          console.error('❌ Falha ao processar warning data');
        }
      }
      
      // ✅ CORREÇÃO: Sucesso sem avisos
      documents.forEach(doc => {
        if (doc.fileUrl) {
          URL.revokeObjectURL(doc.fileUrl);
        }
      });
      
      setDocuments([]);
      setShowReviewModal(false);
      
      if (onUploadSuccess) {
        onUploadSuccess();
      }
      
      // Mostrar resultado detalhado
      let message = result.message || `${result.faturas_processadas?.length || 0} fatura(s) processada(s)`;
      
      if (result.faturas_com_erro && result.faturas_com_erro.length > 0) {
        message += `\n\nErros encontrados:\n${result.faturas_com_erro.map(e => `- ${e.arquivo}: ${e.erro}`).join('\n')}`;
      }
      
      alert(message);
      
    } catch (error) {
      console.error('❌ Erro ao salvar:', error);
      
      // ✅ CORREÇÃO: Tratar erro 409 como aviso, não como erro
      if (error.response?.status === 409) {
        console.log('⚠️ Erro 409 capturado como aviso:', error.response.data);
        const result = error.response.data;
        
        if (result.avisos && result.avisos.length > 0) {
          console.log('🔍 Processando avisos do catch 409:', result.avisos);
          const warningData = processarAvisos(result.avisos, result.faturas_processadas);
          
          if (warningData) {
            console.log('✅ Abrindo modal de aviso (catch):', warningData);
            setWarningModal({
              isOpen: true,
              type: warningData.type,
              data: warningData.data,
              pendingUploads: warningData.pendingUploads,
              isProcessing: false
            });
            
            setIsProcessing(false);
            return;
          } else {
            console.error('❌ Falha ao processar warning data no catch');
          }
        } else {
          // ✅ MELHORIA: Tratar erro 409 mesmo sem o array 'avisos'
          console.log('⚠️ Tentando tratar 409 com a mensagem de erro principal.');
          const errorMessage = result.error || 'Conflito detectado.';
          const warningData = processarAvisos([{
            tipo: 'FATURA_DUPLICADA',
            mensagem: errorMessage,
            arquivo: validDocuments[0]?.fileName // Usa o primeiro arquivo como referência
          }]);

          if (warningData) {
            console.log('✅ Abrindo modal de aviso (catch com fallback):', warningData);
            setWarningModal({
              isOpen: true,
              type: warningData.type,
              data: warningData.data,
              pendingUploads: warningData.pendingUploads,
              isProcessing: false
            });
            setIsProcessing(false);
            return;
          }
        }
      }
      
      alert(error.response?.data?.error || 'Erro ao salvar documentos');
    } finally {
      setIsProcessing(false);
    }
  };

  const currentDoc = documents[activeTab];

  if (!showReviewModal) {
    return (
      <div className="w-full">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-800 mb-2">
            Upload Manual de Faturas
          </h3>
          <p className="text-sm text-gray-600">
            Arraste e solte seus arquivos PDF aqui ou clique para selecionar
          </p>
        </div>
        
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
            isDragActive 
              ? 'border-blue-400 bg-blue-50' 
              : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <FaUpload className={`mx-auto h-12 w-12 mb-4 ${
            isDragActive ? 'text-blue-500' : 'text-gray-400'
          }`} />
          <p className="text-lg text-gray-600 mb-2">
            {isDragActive ? 'Solte os arquivos aqui!' : 'Arraste e solte seus PDFs aqui'}
          </p>
          <p className="text-gray-500">ou clique para selecionar arquivos</p>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
        
        {isProcessing && (
          <div className="mt-6 text-center">
            <div className="inline-flex items-center px-4 py-2 bg-blue-100 rounded-lg">
              <FaSpinner className="animate-spin h-4 w-4 text-blue-600 mr-2" />
              <span className="text-blue-800">Processando faturas...</span>
            </div>
          </div>
        )}

        {/* Modal de Avisos */}
        <WarningModal
          isOpen={warningModal.isOpen}
          onClose={() => setWarningModal(prev => ({ ...prev, isOpen: false }))}
          onConfirm={handleWarningConfirm}
          warningType={warningModal.type}
          warningData={warningModal.data}
          isProcessing={warningModal.isProcessing}
        />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full h-full max-w-7xl max-h-[90vh] m-4 flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-bold text-gray-800">
            Revisão de Faturas ({documents.length})
          </h2>
          <button
            onClick={() => setShowReviewModal(false)}
            className="text-gray-500 hover:text-gray-700"
          >
            <FaTimes className="h-6 w-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b bg-gray-50 overflow-x-auto">
          {documents.map((doc, index) => (
            <div
              key={doc.id}
              className={`flex items-center px-4 py-2 text-sm font-medium whitespace-nowrap cursor-pointer ${
                activeTab === index
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-white'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
              onClick={() => setActiveTab(index)}
            >
              <FaFilePdf className="h-4 w-4 mr-2 text-red-500" />
              <span>{doc.fileName}</span>
              {doc.status === 'error' && (
                <div className="h-2 w-2 bg-red-500 rounded-full ml-2"></div>
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeDocument(doc.id);
                }}
                className="ml-2 text-gray-400 hover:text-red-500 p-1"
              >
                <FaTimes className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel - Form */}
          <div className="w-1/2 p-6 overflow-y-auto border-r">
            {currentDoc?.status === 'error' ? (
              <div className="text-center py-12">
                <div className="h-12 w-12 text-red-500 mx-auto mb-4">⚠️</div>
                <h3 className="text-lg font-medium text-red-800 mb-2">
                  Erro no Processamento
                </h3>
                <p className="text-red-600">{currentDoc.error}</p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-gray-800">
                    Dados da Fatura
                  </h3>
                  <FaEdit className="h-5 w-5 text-gray-400" />
                </div>

                {/* Seção: Informações Básicas */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-800 mb-3">📄 Informações Básicas</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Unidade Consumidora
                      </label>
                      <input
                        type="text"
                        value={currentDoc?.modifiedData?.unidade_consumidora || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'unidade_consumidora', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Mês de Referência
                      </label>
                      <input
                        type="text"
                        placeholder="JAN/2024"
                        value={currentDoc?.modifiedData?.mes_referencia || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'mes_referencia', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Data de Vencimento
                      </label>
                      <input
                        type="text"
                        placeholder="DD/MM/AAAA"
                        value={currentDoc?.modifiedData?.data_vencimento || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'data_vencimento', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Valor Total (R$)
                      </label>
                      <input
                        type="text"
                        value={currentDoc?.modifiedData?.valor_total || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'valor_total', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Seção: Consumo de Energia */}
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-800 mb-3">⚡ Consumo de Energia</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Consumo Total (kWh)
                      </label>
                      <input
                        type="text"
                        value={currentDoc?.modifiedData?.consumo_kwh || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'consumo_kwh', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Saldo de Energia (kWh)
                      </label>
                      <input
                        type="text"
                        value={currentDoc?.modifiedData?.saldo_kwh || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'saldo_kwh', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Seção: Energia Solar (SCEE) */}
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-800 mb-3">☀️ Energia Solar (SCEE)</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Energia Injetada (kWh)
                      </label>
                      <input
                        type="text"
                        value={currentDoc?.modifiedData?.energia_injetada || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'energia_injetada', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Consumo SCEE (kWh)
                      </label>
                      <input
                        type="text"
                        value={currentDoc?.modifiedData?.consumo_scee || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'consumo_scee', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Seção: Informações do Cliente */}
                <div className="bg-purple-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-800 mb-3">👤 Informações do Cliente</h4>
                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Nome do Cliente
                      </label>
                      <input
                        type="text"
                        value={currentDoc?.modifiedData?.nome_cliente || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'nome_cliente', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        CPF/CNPJ
                      </label>
                      <input
                        type="text"
                        value={currentDoc?.modifiedData?.cpf_cnpj || ''}
                        onChange={(e) => updateDocumentData(currentDoc.id, 'cpf_cnpj', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel - PDF Viewer */}
          <div className="w-1/2 p-6">
            <div className="h-full bg-gray-100 rounded-lg overflow-hidden">
              {currentDoc?.fileUrl ? (
                <iframe
                  src={currentDoc.fileUrl}
                  className="w-full h-full border-none"
                  title={`PDF Viewer - ${currentDoc.fileName}`}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center">
                    <FaEye className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                    <p>Nenhum documento selecionado</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center p-4 border-t bg-gray-50">
          <button
            onClick={() => setShowReviewModal(false)}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            Cancelar
          </button>
          
          <div className="flex space-x-4">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 bg-blue-100 text-blue-800 rounded-md hover:bg-blue-200"
            >
              Adicionar Mais PDFs
            </button>
            
            <button
              onClick={saveAllDocuments}
              disabled={isProcessing || documents.length === 0}
              className="flex items-center px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
            >
              {isProcessing ? (
                <>
                  <FaSpinner className="animate-spin h-4 w-4 mr-2" />
                  Salvando...
                </>
              ) : (
                <>
                  <FaSave className="h-4 w-4 mr-2" />
                  Salvar Todas ({documents.filter(d => d.status === 'reviewed').length})
                </>
              )}
            </button>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Modal de Avisos */}
        <WarningModal
          isOpen={warningModal.isOpen}
          onClose={() => {
            console.log('🔒 Fechando WarningModal');
            setWarningModal(prev => ({ ...prev, isOpen: false }));
          }}
          onConfirm={handleWarningConfirm}
          warningType={warningModal.type}
          warningData={warningModal.data}
          isProcessing={warningModal.isProcessing}
        />
      </div>
    </div>
  );
};

export default FaturaUpload;