import { useState } from 'react';
import { Link } from 'react-router-dom';
import InputField from '../components/InputField';
import { apiClient } from '../services/api'; // Corrected import

function RegisterPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');

    if (password !== confirmPassword) {
      setError('As senhas não correspondem.');
      return;
    }
    try {
      // Corrigido o endpoint da API para /register/
      await apiClient.post('/register/', { username, email, password });
      setMessage('Registro bem-sucedido! Por favor, verifique seu e-mail para ativar sua conta.');
      setError('');
      // Limpa os campos após o sucesso
      setUsername('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError('Ocorreu um erro ao registrar. Verifique os dados e tente novamente.');
      setMessage('');
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-3xl font-bold text-indigo-600 mb-6 text-center">Criar Conta</h1>
        
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

        <form onSubmit={handleRegister} className="space-y-5">
          <div>
            <InputField
              placeholder="Nome de usuário"
              value={username}
              onChange={setUsername}
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
          <div className="mt-6">
            <button
              type="submit"
              className="w-full bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Cadastrar
            </button>
          </div>
        </form>

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
