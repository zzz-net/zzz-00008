import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import ToastContainer from '@/components/ToastContainer';
import Dashboard from '@/pages/Dashboard';
import TicketList from '@/pages/TicketList';
import TicketCreate from '@/pages/TicketCreate';
import TicketDetail from '@/pages/TicketDetail';
import BatchList from '@/pages/BatchList';
import BatchCreate from '@/pages/BatchCreate';
import BatchDetail from '@/pages/BatchDetail';
import ShiftList from '@/pages/ShiftList';
import ReminderList from '@/pages/ReminderList';
import PlanList from '@/pages/PlanList';

export default function App() {
  return (
    <Router>
      <ToastContainer />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/tickets" element={<TicketList />} />
          <Route path="/tickets/create" element={<TicketCreate />} />
          <Route path="/tickets/:id" element={<TicketDetail />} />
          <Route path="/batches" element={<BatchList />} />
          <Route path="/batches/create" element={<BatchCreate />} />
          <Route path="/batches/:id" element={<BatchDetail />} />
          <Route path="/shifts" element={<ShiftList />} />
          <Route path="/reminders" element={<ReminderList />} />
          <Route path="/plans" element={<PlanList />} />
        </Route>
      </Routes>
    </Router>
  );
}
