import React, { useEffect, useState } from 'react'
import InspectionList from './pages/InspectionList'
import InspectionUpload from './pages/InspectionUpload'
import ResultViewer from './pages/ResultViewer'
import ModelManagement from './pages/ModelManagement'
import AuthPanel from './pages/AuthPanel'
import { AuthUser } from './api'
import './App.css'

type Page = 'list' | 'upload' | 'result' | 'models'

interface ResultViewerState {
  jobId: string
  inspectionId: string
}

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('list')
  const [resultViewerState, setResultViewerState] = useState<ResultViewerState | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [user, setUser] = useState<AuthUser | null>(() => {
    const storedUser = localStorage.getItem('current_user')
    return storedUser ? JSON.parse(storedUser) as AuthUser : null
  })

  useEffect(() => {
    const handleLogout = () => setUser(null)
    window.addEventListener('forgesight:logout', handleLogout)
    return () => window.removeEventListener('forgesight:logout', handleLogout)
  }, [])

  const handleUploadSuccess = () => {
    setCurrentPage('list')
    setRefreshTrigger(r => r + 1)
  }

  const handleViewResult = (jobId: string, inspectionId: string) => {
    setResultViewerState({ jobId, inspectionId })
    setCurrentPage('result')
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('current_user')
    setUser(null)
    setCurrentPage('list')
    setResultViewerState(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>ForgeSight</h1>
          <p className="tagline">AI-assisted visual inspection & defect triage</p>
        </div>
        {user && (
          <div className="user-menu">
            <span>{user.displayName || user.email}</span>
            <button type="button" className="btn btn-ghost" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        )}
      </header>

      {user && (
        <nav className="app-nav">
          <button
            className={`nav-button ${currentPage === 'list' ? 'active' : ''}`}
            onClick={() => setCurrentPage('list')}
          >
            Inspections
          </button>
          <button
            className={`nav-button ${currentPage === 'upload' ? 'active' : ''}`}
            onClick={() => setCurrentPage('upload')}
          >
            New Inspection
          </button>
          <button
            className={`nav-button ${currentPage === 'models' ? 'active' : ''}`}
            onClick={() => setCurrentPage('models')}
          >
            Models
          </button>
        </nav>
      )}

      <main className="app-content">
        {!user && <AuthPanel onAuthenticated={setUser} />}
        {user && currentPage === 'list' && (
          <InspectionList onViewResult={handleViewResult} refreshTrigger={refreshTrigger} />
        )}
        {user && currentPage === 'upload' && <InspectionUpload onSuccess={handleUploadSuccess} />}
        {user && currentPage === 'result' && resultViewerState && (
          <ResultViewer jobId={resultViewerState.jobId} inspectionId={resultViewerState.inspectionId} />
        )}
        {user && currentPage === 'models' && <ModelManagement />}
      </main>

      <footer className="app-footer">
        <p>&copy; 2026 ForgeSight. All rights reserved.</p>
      </footer>
    </div>
  )
}
