// frontend/src/App.jsx
import { Outlet } from 'react-router-dom';

function App() {
  return (
    <div className="min-h-screen bg-gray-100 p-8">
     
      
      <div className="bg-white p-6 rounded-lg shadow-md max-w-6xl mx-auto">
        <main>
          {/* O Outlet renderiza a rota filha correspondente (ex: a página de cadastro) */}
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default App;