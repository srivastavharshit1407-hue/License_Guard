import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Alerts from './pages/Alerts'
import Applications from './pages/Applications'
import Connections from './pages/Connections'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import Licenses from './pages/Licenses'
import Login from './pages/Login'
import Signup from './pages/Signup'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/applications" element={<Applications />} />
        <Route path="/licenses" element={<Licenses />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/connections" element={<Connections />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
