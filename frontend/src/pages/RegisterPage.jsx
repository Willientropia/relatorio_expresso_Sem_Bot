import { useState } from 'react';
import { Link } from 'react-router-dom';
import InputField from '../components/InputField';

function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleRegister = () => {
    // Lógica de cadastro será implementada aqui
    console.log('Registrando com:', { name, email, password });
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-3xl font-bold text-indigo-600 mb-6 text-center">Criar Conta</h1>
        
        <div className="space-y-5">
          <div>
            <InputField
              placeholder="Nome completo"
              value={name}
              onChange={setName}
            />
          </div>
          <div>
            <InputField
              placeholder="seu@email.com"
              value={email}
              onChange={setEmail}
              type="email"
            />
          </div>
          <div>
            <InputField
              placeholder="Senha"
              value={password}
              onChange={setPassword}
              type="password"
            />
          </div>
          <div>
            <InputField
              placeholder="Confirme a senha"
              value={confirmPassword}
              onChange={setConfirmPassword}
              type="password"
            />
          </div>
        </div>

        <div className="mt-6">
          <button
            onClick={handleRegister}
            className="w-full bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Cadastrar
          </button>
        </div>

        <p className="text-center text-sm text-gray-600 mt-4">
          Já tem uma conta?{' '}
          <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
            Faça login
          </Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
