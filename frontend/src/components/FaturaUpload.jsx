import React, { useState, useCallback, useRef } from 'react';
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
    pendingUpload: null
  });
  const fileInputRef = useRef(null);

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

  // ✅ FUNÇÃO COMPLETA handleWarningConfirm
  const handleWarningConfirm = async () => {
    const { pendingUpload } = warningModal;
    if (!pendingUpload) {
      console.error('❌ Nenhum upload pendente encontrado');
      return;
    }

    console.log('🔧 DEBUG handleWarningConfirm:', pendingUpload);
    
    setWarningModal(prev => ({ ...prev, isProcessing: true }));

    try {
      const formData = new FormData();
      
      // Adicionar arquivo
      formData.append('arquivo', pendingUpload.file);
      
      // Adicionar UC código
      formData.append('uc_codigo', pendingUpload.uc_codigo);
      
      // Adicionar mês de referência no formato correto
      formData.append('mes_referencia', pendingUpload.mes_referencia);
      
      // Adicionar dados extraídos como JSON string
      if (pendingUpload.dados_extraidos) {
        formData.append('dados_extraidos', JSON.stringify(pendingUpload.dados_extraidos));
      }
      
      // Debug: Log dos dados sendo enviados
      console.log('📤 Enviando dados:', {
        uc_codigo: pendingUpload.uc_codigo,
        mes_referencia: pendingUpload.mes_referencia,
        arquivo_name: pendingUpload.file.name,
        arquivo_size: pendingUpload.file.size,
        dados_extraidos: pendingUpload.dados_extraidos
      });

      const response = await apiClient.post(
        `/customers/${clienteId}/faturas/force-upload/`,
        formData,
        {
          headers: { 
            'Content-Type': 'multipart/form-data' 
          },
          timeout: 60000 // 60 segundos de timeout
        }
      );

      if (response.status === 201) {
        console.log('✅ Upload forçado bem-sucedido:', response.data);
        
        // Limpar URLs de objeto
        documents.forEach(doc => {
          if (doc.fileUrl) {
            URL.revokeObjectURL(doc.fileUrl);
          }
        });
        
        // Resetar estados
        setDocuments([]);
        setShowReviewModal(false);
        setWarningModal({
          isOpen: false,
          type: null,
          data: null,
          pendingUpload: null
        });
        
        // Chamar callback de sucesso
        if (onUploadSuccess) {
          onUploadSuccess();
        }
        
        // Mostrar mensagem de sucesso
        alert('Fatura substituída com sucesso!');
      } else {
        console.error('❌ Resposta inesperada:', response);
        throw new Error(`Status inesperado: ${response.status}`);
      }
      
    } catch (error) {
      console.error('❌ Erro ao forçar upload:', error);
      
      let errorMessage = 'Erro desconhecido ao enviar fatura';
      
      if (error.response) {
        // Servidor respondeu com erro
        console.error('Erro do servidor:', error.response.data);
        errorMessage = error.response.data?.error || 
                      `Erro do servidor: ${error.response.status}`;
      } else if (error.request) {
        // Request foi feito mas sem resposta
        console.error('Sem resposta do servidor:', error.request);
        errorMessage = 'Erro de rede: Sem resposta do servidor';
      } else {
        // Erro ao configurar request
        console.error('Erro de configuração:', error.message);
        errorMessage = `Erro: ${error.message}`;
      }
      
      alert(errorMessage);
      
    } finally {
      setWarningModal(prev => ({ ...prev, isProcessing: false }));
    }
  };

  // ✅ FUNÇÃO COMPLETA saveAllDocuments
  const saveAllDocuments = async () => {
    console.log('🔧 === INÍCIO DEBUG SAVEALL ===');
    
    // PASSO 1: Verificar documentos
    const validDocuments = documents.filter(doc => doc.status === 'reviewed');
    console.log('PASSO 1 - Documentos:', {
      total: documents.length,
      validos: validDocuments.length,
      documentos: documents.map(d => ({
        fileName: d.fileName,
        status: d.status,
        hasFile: !!d.file,
        fileSize: d.file?.size,
        fileType: d.file?.type
      }))
    });
    
    if (validDocuments.length === 0) {
      console.error('❌ PASSO 1 FALHOU: Nenhum documento válido');
      alert('Nenhum documento válido para salvar');
      return;
    }
    
    // PASSO 2: Verificar cliente ID
    console.log('PASSO 2 - Cliente ID:', {
      clienteId,
      tipo: typeof clienteId,
      isNumber: !isNaN(clienteId),
      isString: typeof clienteId === 'string'
    });
    
    if (!clienteId) {
      console.error('❌ PASSO 2 FALHOU: Cliente ID inválido');
      alert('Erro: ID do cliente não definido');
      return;
    }
    
    // PASSO 3: Verificar autenticação
    const accessToken = localStorage.getItem('accessToken');
    console.log('PASSO 3 - Autenticação:', {
      hasToken: !!accessToken,
      tokenPreview: accessToken ? `${accessToken.substring(0, 20)}...` : 'SEM TOKEN'
    });
    
    if (!accessToken) {
      console.error('❌ PASSO 3 FALHOU: Sem token de acesso');
      alert('Erro: Usuário não autenticado. Faça login novamente.');
      return;
    }

    setIsProcessing(true);
    
    try {
      // PASSO 4: Criar FormData
      console.log('PASSO 4 - Criando FormData...');
      const formData = new FormData();
      
      validDocuments.forEach((doc, index) => {
        console.log(`📎 PASSO 4.${index + 1} - Adicionando:`, {
          fileName: doc.fileName,
          fileSize: doc.file.size,
          fileType: doc.file.type,
          lastModified: doc.file.lastModified
        });
        
        // Verificar se o arquivo ainda é válido
        if (!doc.file || doc.file.size === 0) {
          throw new Error(`Arquivo ${doc.fileName} é inválido ou vazio`);
        }
        
        formData.append('faturas', doc.file);
      });
      
      console.log('✅ PASSO 4 CONCLUÍDO - FormData criado');
      
      // PASSO 5: Preparar URL e headers
      const url = `/customers/${clienteId}/faturas/upload-with-extraction/`;
      const headers = { 
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${accessToken}`
      };
      
      console.log('PASSO 5 - Preparando requisição:', {
        url,
        method: 'POST',
        headers: headers,
        formDataEntries: formData.has('faturas') ? 'Arquivos presentes' : 'ERRO: Sem arquivos'
      });
      
      // PASSO 6: Fazer a requisição
      console.log('PASSO 6 - Enviando requisição...');
      console.time('⏱️ Tempo de upload');
      
      const response = await apiClient.post(url, formData, {
        headers: headers,
        timeout: 120000,
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          if (percentCompleted % 10 === 0) { // Log a cada 10%
            console.log(`📊 Upload: ${percentCompleted}%`);
          }
        }
      });
      
      console.timeEnd('⏱️ Tempo de upload');
      console.log('✅ PASSO 6 CONCLUÍDO - Resposta recebida:', {
        status: response.status,
        statusText: response.statusText,
        dataKeys: Object.keys(response.data || {})
      });
      
      // PASSO 7: Processar resposta
      console.log('PASSO 7 - Processando resposta...');
      const result = response.data;
      
      console.log('📥 Dados completos da resposta:', result);
      
      // ✅ NOVO: Verificar se há avisos e tratá-los adequadamente
      if (result.avisos && result.avisos.length > 0) {
        console.log('⚠️ Avisos encontrados:', result.avisos);
        const primeiroAviso = result.avisos[0];
        
        // ✅ NOVO: Diferentes tipos de avisos
        if (primeiroAviso.tipo === 'fatura_duplicada') {
          // Encontrar documento correspondente
          const docCorrespondente = validDocuments.find(doc => 
            doc.fileName === primeiroAviso.arquivo
          );
          
          if (docCorrespondente) {
            console.log('🔍 Documento correspondente encontrado:', docCorrespondente.fileName);
            
            const dadosParaForceUpload = {
              file: docCorrespondente.file,
              uc_codigo: primeiroAviso.uc_codigo,
              mes_referencia: primeiroAviso.mes_referencia,
              dados_extraidos: docCorrespondente.extractedData || docCorrespondente.modifiedData
            };
            
            console.log('📋 Dados preparados para force upload:', {
              uc_codigo: dadosParaForceUpload.uc_codigo,
              mes_referencia: dadosParaForceUpload.mes_referencia,
              arquivo: dadosParaForceUpload.file.name
            });
            
            setWarningModal({
              isOpen: true,
              type: 'fatura_duplicada',
              data: primeiroAviso,
              pendingUpload: dadosParaForceUpload
            });
          } else {
            console.error('❌ Documento correspondente não encontrado para:', primeiroAviso.arquivo);
            alert('Erro: Não foi possível encontrar o documento correspondente ao aviso');
          }
          
          setIsProcessing(false);
          return;
        }
        
        // ✅ NOVO: UC pertence a outro cliente - apenas informativo
        if (primeiroAviso.tipo === 'uc_outro_cliente') {
          console.log('⚠️ UC pertence a outro cliente:', primeiroAviso);
          setWarningModal({
            isOpen: true,
            type: 'uc_outro_cliente',
            data: primeiroAviso,
            pendingUpload: null
          });
          
          setIsProcessing(false);
          return;
        }
        
        // ✅ NOVO: UC não encontrada - apenas informativo
        if (primeiroAviso.tipo === 'uc_nao_encontrada') {
          console.log('⚠️ UC não encontrada no sistema:', primeiroAviso);
          setWarningModal({
            isOpen: true,
            type: 'uc_nao_encontrada',
            data: primeiroAviso,
            pendingUpload: null
          });
          
          setIsProcessing(false);
          return;
        }
      }
      
      // ✅ MANTIDO: Verificar se há faturas com avisos de UC outro cliente (compatibilidade)
      if (result.faturas_processadas) {
        const faturasComAviso = result.faturas_processadas.filter(f => f.aviso);
        
        if (faturasComAviso.length > 0) {
          const faturaComAviso = faturasComAviso[0];
          
          if (faturaComAviso.aviso.tipo === 'uc_outro_cliente') {
            const avisoDetalhado = {
              ...faturaComAviso.aviso,
              faturas_afetadas: faturasComAviso.length,
              detalhes_faturas: faturasComAviso.map(f => ({
                arquivo: f.arquivo,
                uc: f.uc,
                mes_referencia: f.mes_referencia,
                fatura_id: f.id
              }))
            };
            
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
            
            setWarningModal({
              isOpen: true,
              type: 'uc_outro_cliente_info',
              data: avisoDetalhado,
              pendingUpload: null
            });
            
            setIsProcessing(false);
            return;
          }
        }
      }
      
      console.log('✅ Upload concluído sem avisos');
      
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
      
      // ✅ MELHORADO: Mostrar resultado detalhado
      let message = result.message || 'Upload concluído com sucesso';
      
      if (result.faturas_com_erro && result.faturas_com_erro.length > 0) {
        message += `\n\nErros encontrados:\n${result.faturas_com_erro.map(e => `- ${e.arquivo}: ${e.erro}`).join('\n')}`;
      }
      
      if (result.faturas_processadas && result.faturas_processadas.length > 0) {
        message += `\n\nFaturas processadas: ${result.faturas_processadas.length}`;
      }
      
      // ✅ NOVO: Mostrar avisos informativos (não bloqueantes)
      if (result.avisos && result.avisos.length > 0) {
        const avisosInfo = result.avisos.filter(a => 
          a.tipo === 'uc_nao_encontrada' || a.tipo === 'uc_outro_cliente'
        );
        
        if (avisosInfo.length > 0) {
          message += `\n\nAvisos:\n${avisosInfo.map(a => `- ${a.arquivo}: ${a.mensagem}`).join('\n')}`;
        }
      }
      
      alert(message);
      
      console.log('✅ === SUCESSO COMPLETO ===');
      
    } catch (error) {
      console.timeEnd('⏱️ Tempo de upload');
      console.error('❌ === ERRO DETECTADO ===');
      
      // ANÁLISE DETALHADA DO ERRO
      console.error('🔍 Análise completa do erro:');
      console.error('  Tipo:', error.constructor.name);
      console.error('  Mensagem:', error.message);
      console.error('  Code:', error.code);
      console.error('  Config URL:', error.config?.url);
      console.error('  Config Method:', error.config?.method);
      
      if (error.response) {
        console.error('📥 RESPOSTA DO SERVIDOR:');
        console.error('  Status:', error.response.status);
        console.error('  Status Text:', error.response.statusText);
        console.error('  Headers:', error.response.headers);
        console.error('  Data:', error.response.data);
        
        // Análise específica do erro 400
        if (error.response.status === 400) {
          console.error('🔍 ANÁLISE ERRO 400:');
          console.error('  - Verificar se cliente ID é válido');
          console.error('  - Verificar se usuário tem permissão');
          console.error('  - Verificar se arquivos foram enviados corretamente');
          console.error('  - Verificar se arquivos são PDFs válidos');
          
          const errorData = error.response.data;
          if (errorData && errorData.error) {
            alert(`Erro 400: ${errorData.error}`);
          } else {
            alert('Erro 400: Requisição inválida. Verifique os logs do console para mais detalhes.');
          }
        } else {
          // ✅ MELHORADO: Tratamento de outros erros
          let errorMessage = 'Erro ao salvar documentos';
          
          if (error.response.data?.error) {
            errorMessage = error.response.data.error;
          } else if (error.response.data?.avisos) {
            // Se o erro vier como avisos
            const avisos = error.response.data.avisos;
            errorMessage = avisos.map(a => a.mensagem).join('\n');
          } else if (error.response.data?.detail) {
            errorMessage = error.response.data.detail;
          }
          
          alert(errorMessage);
        }
      } else if (error.request) {
        console.error('📡 SEM RESPOSTA DO SERVIDOR:');
        console.error('  Request:', error.request);
        alert('Erro: Sem resposta do servidor. Verifique sua conexão.');
      } else {
        console.error('⚙️ ERRO DE CONFIGURAÇÃO:');
        console.error('  Detalhes:', error.message);
        alert(`Erro de configuração: ${error.message}`);
      }
      
      console.error('❌ === FIM ANÁLISE ERRO ===');
      
    } finally {
      setIsProcessing(false);
      console.log('🔧 === FIM DEBUG SAVEALL ===');
    }
  };

  
  // Função para renderizar campos por seção
  const renderFieldSection = (sectionTitle, sectionIcon, fields, bgColor = 'bg-gray-50') => {
    const currentDoc = documents[activeTab];
    
    return (
      <div className={`${bgColor} p-4 rounded-lg mb-6`}>
        <div className="flex items-center mb-4">
          {sectionIcon}
          <h4 className="font-medium text-gray-800 ml-2">{sectionTitle}</h4>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {fields.map(({ field, label, placeholder, type = 'text' }) => (
            <div key={field}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {label}
              </label>
              <input
                type={type}
                placeholder={placeholder}
                value={currentDoc?.modifiedData?.[field] || ''}
                onChange={(e) => updateDocumentData(currentDoc.id, field, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
          ))}
        </div>
      </div>
    );
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
            Revisão Completa de Faturas ({documents.length})
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
          {/* Left Panel - Formulário Completo */}
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
                    Dados Completos da Fatura
                  </h3>
                  <FaEdit className="h-5 w-5 text-gray-400" />
                </div>

                {/* Seção: Informações Básicas */}
                {renderFieldSection(
                  'Informações Básicas',
                  <FaFilePdf className="h-5 w-5 text-gray-600" />,
                  [
                    { field: 'unidade_consumidora', label: 'Unidade Consumidora', placeholder: 'Ex: 123456789' },
                    { field: 'mes_referencia', label: 'Mês de Referência', placeholder: 'Ex: JAN/2024' },
                    { field: 'data_vencimento', label: 'Data de Vencimento', placeholder: 'DD/MM/AAAA' },
                    { field: 'valor_total', label: 'Valor Total (R$)', placeholder: 'Ex: 150.25' },
                    { field: 'distribuidora', label: 'Distribuidora', placeholder: 'Ex: Equatorial Energia' },
                    { field: 'arquivo_processado', label: 'Arquivo Processado', placeholder: 'Nome do arquivo' }
                  ],
                  'bg-blue-50'
                )}

                {/* Seção: Informações do Cliente */}
                {renderFieldSection(
                  'Informações do Cliente',
                  <FaUser className="h-5 w-5 text-purple-600" />,
                  [
                    { field: 'nome_cliente', label: 'Nome do Cliente', placeholder: 'Nome completo' },
                    { field: 'cpf_cnpj', label: 'CPF/CNPJ', placeholder: '000.000.000-00' },
                    { field: 'endereco_cliente', label: 'Endereço', placeholder: 'Endereço completo' }
                  ],
                  'bg-purple-50'
                )}

                {/* Seção: Consumo de Energia */}
                {renderFieldSection(
                  'Consumo de Energia',
                  <FaBolt className="h-5 w-5 text-yellow-600" />,
                  [
                    { field: 'consumo_kwh', label: 'Consumo Total (kWh)', placeholder: 'Ex: 250.5' },
                    { field: 'saldo_kwh', label: 'Saldo de Energia (kWh)', placeholder: 'Ex: 150.0' },
                    { field: 'consumo_nao_compensado', label: 'Consumo Não Compensado (kWh)', placeholder: 'Ex: 100.0' },
                    { field: 'preco_kwh_nao_compensado', label: 'Preço kWh Não Compensado (R$)', placeholder: 'Ex: 0.75' }
                  ],
                  'bg-yellow-50'
                )}

                {/* Seção: Energia Solar (SCEE) */}
                {renderFieldSection(
                  'Energia Solar (SCEE)',
                  <FaIndustry className="h-5 w-5 text-green-600" />,
                  [
                    { field: 'energia_injetada', label: 'Energia Injetada (kWh)', placeholder: 'Ex: 200.0' },
                    { field: 'preco_energia_injetada', label: 'Preço Energia Injetada (R$)', placeholder: 'Ex: 120.50' },
                    { field: 'consumo_scee', label: 'Consumo SCEE (kWh)', placeholder: 'Ex: 180.0' },
                    { field: 'preco_energia_compensada', label: 'Preço Energia Compensada (R$)', placeholder: 'Ex: 108.00' }
                  ],
                  'bg-green-50'
                )}

                {/* Seção: Valores Financeiros */}
                {renderFieldSection(
                  'Valores Financeiros',
                  <FaDollarSign className="h-5 w-5 text-red-600" />,
                  [
                    { field: 'contribuicao_iluminacao', label: 'Contribuição Iluminação Pública (R$)', placeholder: 'Ex: 25.00' },
                    { field: 'preco_fio_b', label: 'Preço Fio B (R$)', placeholder: 'Ex: 15.50' },
                    { field: 'preco_adc_bandeira', label: 'Preço ADC Bandeira (R$)', placeholder: 'Ex: 8.75' }
                  ],
                  'bg-red-50'
                )}

                {/* Seção: Informações de Leitura */}
                {renderFieldSection(
                  'Informações de Leitura',
                  <FaCalendarAlt className="h-5 w-5 text-indigo-600" />,
                  [
                    { field: 'leitura_anterior', label: 'Leitura Anterior', placeholder: 'DD/MM/AAAA' },
                    { field: 'leitura_atual', label: 'Leitura Atual', placeholder: 'DD/MM/AAAA' },
                    { field: 'quantidade_dias', label: 'Quantidade de Dias', placeholder: 'Ex: 30' }
                  ],
                  'bg-indigo-50'
                )}

                {/* Seção: Geração Solar */}
                {renderFieldSection(
                  'Geração Solar',
                  <FaCalculator className="h-5 w-5 text-orange-600" />,
                  [
                    { field: 'ciclo_geracao', label: 'Ciclo de Geração', placeholder: 'Ex: 01/2024' },
                    { field: 'uc_geradora', label: 'UC Geradora', placeholder: 'Ex: 987654321' },
                    { field: 'geracao_ultimo_ciclo', label: 'Geração Último Ciclo (kWh)', placeholder: 'Ex: 300.0' }
                  ],
                  'bg-orange-50'
                )}

                {/* Status da Extração */}
                <div className="bg-gray-100 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-800 mb-2">📊 Status da Extração</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Status:</span>
                      <span className={`ml-2 px-2 py-1 rounded text-xs ${
                        currentDoc?.extractedData?.status === 'success' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {currentDoc?.extractedData?.status || 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Campos Extraídos:</span>
                      <span className="ml-2 font-medium">
                        {currentDoc?.extractedData ? 
                          Object.keys(currentDoc.extractedData).filter(key => 
                            key !== 'status' && key !== 'dados_completos' && currentDoc.extractedData[key]
                          ).length : 0
                        }
                      </span>
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

        <WarningModal
          isOpen={warningModal.isOpen}
          onClose={() => setWarningModal(prev => ({ ...prev, isOpen: false }))}
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