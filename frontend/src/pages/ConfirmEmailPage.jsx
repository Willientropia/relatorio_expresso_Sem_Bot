import React from 'react';
import { Link } from 'react-router-dom';

const ConfirmEmailPage = () => {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded shadow-md text-center">
        <h1 className="text-2xl font-bold mb-4">Confirmação de E-mail</h1>
        <p>Ocorreu um erro ao confirmar seu e-mail. O link pode ser inválido ou ter expirado.</p>
        <Link to="/register" className="mt-4 inline-block bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
          Tente se registrar novamente
        </Link>
      </div>
    </div>
  );
};

export default ConfirmEmailPage;
