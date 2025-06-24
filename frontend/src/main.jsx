import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import ClientProfile from './pages/ClientProfile'
import CustomerRegistration from './pages/CustomerRegistration'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Router>
      <Routes>
        {/* Rotas Públicas */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Redireciona a rota raiz para a página de login */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Rotas Privadas (dentro do layout do App) */}
        <Route element={<App />}>
          <Route path="customer-registration" element={<CustomerRegistration />} />
          <Route path=" /:id" element={<ClientProfile />} />
        </Route>
      </Routes>
    </Router>
  </StrictMode>,
)
