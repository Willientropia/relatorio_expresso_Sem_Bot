import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import InputField from '../components/InputField';
import { apiClient } from '../services/api';

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('confirmed') === 'true') {
      setMessage('E-mail confirmado com sucesso! Você já pode fazer o login.');
    }
    if (params.get('already_confirmed') === 'true') {
      setMessage('Este e-mail já foi confirmado. Você pode fazer o login.');
    }
  }, [location]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    try {
      const response = await apiClient.post('/login/', {
        username: email,
        password,
      });
      // Armazena os tokens no localStorage
      localStorage.setItem('accessToken', response.data.access);
      localStorage.setItem('refreshToken', response.data.refresh);
      // Redireciona para a página de cadastro de cliente
      navigate('/customer-registration');
    } catch (err) {
      setError('Falha no login. Verifique seu e-mail e senha.');
      console.error('Login error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-3xl font-bold text-indigo-600 mb-6 text-center">Login</h1>
        
        {message && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4" role="alert">
            <span className="block sm:inline">{message}</span>
          </div>
        )}

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin}>
          <div className="space-y-5">
            <div>
              <InputField
                placeholder="seu@email.com"
                value={email}
                onChange={setEmail}
                type="email"
                required
              />
            </div>
            <div>
              <InputField
                placeholder="Senha"
                value={password}
                onChange={setPassword}
                type="password"
                required
              />
            </div>
          </div>

          <div className="mt-6">
            <button
              type="submit"
              className="w-full bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Entrar
            </button>
          </div>
        </form>

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
