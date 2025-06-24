import { useState } from 'react';
import { Link } from 'react-router-dom';
import InputField from '../components/InputField';

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = () => {
    // Lógica de login será implementada aqui
    console.log('Login com:', { email, password });
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-3xl font-bold text-indigo-600 mb-6 text-center">Login</h1>
        
        <div className="space-y-5">
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
        </div>

        <div className="mt-6">
          <button
            onClick={handleLogin}
            className="w-full bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Entrar
          </button>
        </div>

        <p className="text-center text-sm text-gray-600 mt-4">
          Não tem uma conta?{' '}
          <Link to="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
            Cadastre-se
          </Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
