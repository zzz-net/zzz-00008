import { StrictMode, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';
import { useAuthStore } from './store/useAuthStore';

function AppInitializer() {
  const fetchCurrentUser = useAuthStore((state) => state.fetchCurrentUser);
  const fetchRoles = useAuthStore((state) => state.fetchRoles);
  const fetchUsers = useAuthStore((state) => state.fetchUsers);

  useEffect(() => {
    const initAuth = async () => {
      await fetchCurrentUser();
      await fetchRoles();
      await fetchUsers();
    };
    initAuth();
  }, [fetchCurrentUser, fetchRoles, fetchUsers]);

  return <App />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppInitializer />
  </StrictMode>,
);
