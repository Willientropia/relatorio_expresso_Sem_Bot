import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FaUpload, FaFilePdf, FaSpinner } from 'react-icons/fa';
import { apiClient as api } from '../services/api';

const FaturaUpload = ({ clienteId, onUploadSuccess }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(prevFiles => [...prevFiles, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
  });

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Nenhum arquivo selecionado.');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append('faturas', file);
    });
    formData.append('cliente_id', clienteId);

    try {
      await api.post('/faturas/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setFiles([]);
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (err) {
      setError('Erro ao enviar faturas. Tente novamente.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const removeFile = (fileName) => {
    setFiles(files.filter(file => file.name !== fileName));
  };

  return (
    <div className="p-4 border-dashed border-2 rounded-lg text-center" {...getRootProps()}>
      <input {...getInputProps()} />
      <div className="flex flex-col items-center justify-center h-full">
        <FaUpload className={`w-12 h-12 mb-4 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`} />
        {isDragActive ? (
          <p className="text-lg text-blue-500">Solte os arquivos aqui...</p>
        ) : (
          <p className="text-gray-500">Arraste e solte os arquivos aqui, ou clique para selecionar.</p>
        )}
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          <h3 className="font-semibold">Arquivos selecionados:</h3>
          <ul className="list-disc list-inside">
            {files.map(file => (
              <li key={file.name} className="flex items-center justify-between">
                <span className="flex items-center"><FaFilePdf className="mr-2 text-red-500" /> {file.name}</span>
                <button onClick={(e) => { e.stopPropagation(); removeFile(file.name); }} className="text-red-500 hover:text-red-700">x</button>
              </li>
            ))}
          </ul>

          <div className="mt-4">
            <button
              onClick={handleUpload}
              disabled={loading}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-gray-400"
            >
              {loading ? <FaSpinner className="animate-spin" /> : 'Enviar Faturas'}
            </button>
          </div>
        </div>
      )}

      {error && <p className="text-red-500 mt-2">{error}</p>}

    </div>
  );
};

export default FaturaUpload;
