import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { PageLoader } from './components/Feedback'
import { useAuth } from './contexts/AuthContext'
import { LoginPage } from './pages/LoginPage'
import { ProtectedRoute } from './routes/ProtectedRoute'
import { PublicRoute } from './routes/PublicRoute'

// Cada tela é carregada sob demanda: o login abre sem baixar o painel inteiro.
const AccountPage = lazy(() => import('./pages/AccountPage').then((module) => ({ default: module.AccountPage })))
const AdminAppointmentsPage = lazy(() => import('./pages/AdminAppointmentsPage').then((module) => ({ default: module.AdminAppointmentsPage })))
const AdminBarbersPage = lazy(() => import('./pages/AdminBarbersPage').then((module) => ({ default: module.AdminBarbersPage })))
const AdminBarbershopPage = lazy(() => import('./pages/AdminBarbershopPage').then((module) => ({ default: module.AdminBarbershopPage })))
const AdminClientsPage = lazy(() => import('./pages/AdminClientsPage').then((module) => ({ default: module.AdminClientsPage })))
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage').then((module) => ({ default: module.AdminDashboardPage })))
const AdminServicesPage = lazy(() => import('./pages/AdminServicesPage').then((module) => ({ default: module.AdminServicesPage })))
const AppointmentCreatePage = lazy(() => import('./pages/AppointmentCreatePage').then((module) => ({ default: module.AppointmentCreatePage })))
const BarberAgendaPage = lazy(() => import('./pages/BarberAgendaPage').then((module) => ({ default: module.BarberAgendaPage })))
const BarbersPage = lazy(() => import('./pages/BarbersPage').then((module) => ({ default: module.BarbersPage })))
const HomePage = lazy(() => import('./pages/HomePage').then((module) => ({ default: module.HomePage })))
const MyAppointmentsPage = lazy(() => import('./pages/MyAppointmentsPage').then((module) => ({ default: module.MyAppointmentsPage })))
const OnboardingPage = lazy(() => import('./pages/OnboardingPage').then((module) => ({ default: module.OnboardingPage })))
const PasswordResetConfirmPage = lazy(() => import('./pages/PasswordResetConfirmPage').then((module) => ({ default: module.PasswordResetConfirmPage })))
const PasswordResetRequestPage = lazy(() => import('./pages/PasswordResetRequestPage').then((module) => ({ default: module.PasswordResetRequestPage })))
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((module) => ({ default: module.RegisterPage })))
const ServicesPage = lazy(() => import('./pages/ServicesPage').then((module) => ({ default: module.ServicesPage })))

/** Página inicial de cada perfil: o painel certo, sem uma tela intermediária. */
function RoleHome() {
  const { user } = useAuth()
  if (user?.tipo_perfil === 'admin') return <Navigate to="/admin" replace />
  if (user?.tipo_perfil === 'barbeiro') return <Navigate to="/barber/agenda" replace />
  return <HomePage />
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader label="Carregando…" />}>
      <Routes>
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
        <Route path="/password/reset" element={<PublicRoute><PasswordResetRequestPage /></PublicRoute>} />
        <Route path="/password/reset/confirm" element={<PublicRoute><PasswordResetConfirmPage /></PublicRoute>} />
        <Route path="/onboarding" element={<ProtectedRoute requiresBarbershop={false}><OnboardingPage /></ProtectedRoute>} />
        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route index element={<RoleHome />} />
          <Route path="account" element={<AccountPage />} />
          <Route path="password/change" element={<Navigate to="/account#senha" replace />} />
          <Route path="services" element={<ProtectedRoute allowedRoles={['cliente']}><ServicesPage /></ProtectedRoute>} />
          <Route path="barbers" element={<ProtectedRoute allowedRoles={['cliente']}><BarbersPage /></ProtectedRoute>} />
          <Route path="appointments/new" element={<ProtectedRoute allowedRoles={['cliente']}><AppointmentCreatePage /></ProtectedRoute>} />
          <Route path="appointments" element={<ProtectedRoute allowedRoles={['cliente']}><MyAppointmentsPage /></ProtectedRoute>} />
          <Route path="barber/agenda" element={<ProtectedRoute allowedRoles={['barbeiro']}><BarberAgendaPage /></ProtectedRoute>} />
          <Route path="admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />
          <Route path="admin/appointments" element={<ProtectedRoute allowedRoles={['admin']}><AdminAppointmentsPage /></ProtectedRoute>} />
          <Route path="admin/services" element={<ProtectedRoute allowedRoles={['admin']}><AdminServicesPage /></ProtectedRoute>} />
          <Route path="admin/barbers" element={<ProtectedRoute allowedRoles={['admin']}><AdminBarbersPage /></ProtectedRoute>} />
          <Route path="admin/clients" element={<ProtectedRoute allowedRoles={['admin']}><AdminClientsPage /></ProtectedRoute>} />
          <Route path="admin/barbershop" element={<ProtectedRoute allowedRoles={['admin']}><AdminBarbershopPage /></ProtectedRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
