import { Outlet } from 'react-router-dom';

function App() {
  return (
    <div className="min-h-screen bg-gray-100 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <main className="p-6 sm:p-8">
            {/* O Outlet renderiza a rota filha correspondente (ex: a página de cadastro) */}
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;