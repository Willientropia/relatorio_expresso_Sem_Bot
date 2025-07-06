// frontend/src/components/PrivateRoute.jsx
import React, { useState, useEffect } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { apiClient } from '../services/api';

const PrivateRoute = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(null); // null = loading
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const accessToken = localStorage.getItem('accessToken');
      const refreshToken = localStorage.getItem('refreshToken');

      console.log('🔍 Checking authentication...', {
        hasAccessToken: !!accessToken,
        hasRefreshToken: !!refreshToken
      });

      if (!accessToken && !refreshToken) {
        console.log('❌ No tokens found');
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      try {
        // Tentar fazer uma requisição simples para verificar se o token é válido
        const response = await apiClient.get('/customers/');
        
        console.log('✅ Authentication verified');
        setIsAuthenticated(true);
        
      } catch (error) {
        console.log('❌ Authentication failed:', error.response?.status);
        
        if (error.response?.status === 401) {
          // Token inválido, tentar refresh
          const refreshToken = localStorage.getItem('refreshToken');
          
          if (refreshToken) {
            try {
              console.log('🔄 Trying to refresh token...');
              
              const refreshResponse = await fetch('/api/token/refresh/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh: refreshToken })
              });
              
              if (refreshResponse.ok) {
                const data = await refreshResponse.json();
                localStorage.setItem('accessToken', data.access);
                
                console.log('✅ Token refreshed successfully');
                setIsAuthenticated(true);
              } else {
                console.log('❌ Refresh failed');
                localStorage.removeItem('accessToken');
                localStorage.removeItem('refreshToken');
                setIsAuthenticated(false);
              }
            } catch (refreshError) {
              console.error('❌ Refresh error:', refreshError);
              localStorage.removeItem('accessToken');
              localStorage.removeItem('refreshToken');
              setIsAuthenticated(false);
            }
          } else {
            setIsAuthenticated(false);
          }
        } else {
          setIsAuthenticated(false);
        }
      }

      setIsLoading(false);
    };

    checkAuth();
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Verificando autenticação...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Render protected content
  return <Outlet />;
};

export default PrivateRoute;