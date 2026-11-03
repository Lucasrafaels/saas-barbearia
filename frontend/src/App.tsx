import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { AdminAppointmentsPage } from './pages/AdminAppointmentsPage'
import { AdminBarbersPage } from './pages/AdminBarbersPage'
import { AdminDashboardPage } from './pages/AdminDashboardPage'
import { AdminServicesPage } from './pages/AdminServicesPage'
import { AppointmentCreatePage } from './pages/AppointmentCreatePage'
import { BarberAgendaPage } from './pages/BarberAgendaPage'
import { BarbersPage } from './pages/BarbersPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { MyAppointmentsPage } from './pages/MyAppointmentsPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { PasswordChangePage } from './pages/PasswordChangePage'
import { PasswordResetConfirmPage } from './pages/PasswordResetConfirmPage'
import { PasswordResetRequestPage } from './pages/PasswordResetRequestPage'
import { RegisterPage } from './pages/RegisterPage'
import { ServicesPage } from './pages/ServicesPage'
import { ProtectedRoute } from './routes/ProtectedRoute'
import { PublicRoute } from './routes/PublicRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
      <Route path="/password/reset" element={<PublicRoute><PasswordResetRequestPage /></PublicRoute>} />
      <Route path="/password/reset/confirm" element={<PublicRoute><PasswordResetConfirmPage /></PublicRoute>} />
      <Route path="/onboarding" element={<ProtectedRoute requiresBarbershop={false}><OnboardingPage /></ProtectedRoute>} />
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<HomePage />} />
        <Route path="password/change" element={<ProtectedRoute><PasswordChangePage /></ProtectedRoute>} />
        <Route path="services" element={<ProtectedRoute allowedRoles={['cliente']}><ServicesPage /></ProtectedRoute>} />
        <Route path="barbers" element={<ProtectedRoute allowedRoles={['cliente']}><BarbersPage /></ProtectedRoute>} />
        <Route path="appointments/new" element={<ProtectedRoute allowedRoles={['cliente']}><AppointmentCreatePage /></ProtectedRoute>} />
        <Route path="appointments" element={<ProtectedRoute allowedRoles={['cliente']}><MyAppointmentsPage /></ProtectedRoute>} />
        <Route path="barber/agenda" element={<ProtectedRoute allowedRoles={['barbeiro']}><BarberAgendaPage /></ProtectedRoute>} />
        <Route path="admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />
          <Route path="admin/services" element={<ProtectedRoute allowedRoles={['admin']}><AdminServicesPage /></ProtectedRoute>} />
          <Route path="admin/barbers" element={<ProtectedRoute allowedRoles={['admin']}><AdminBarbersPage /></ProtectedRoute>} />
          <Route path="admin/appointments" element={<ProtectedRoute allowedRoles={['admin']}><AdminAppointmentsPage /></ProtectedRoute>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
