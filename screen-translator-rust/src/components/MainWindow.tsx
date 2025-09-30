import React from 'react'
import { useAppStore } from '../store/appStore'
import HomePage from './pages/HomePage'
import HistoryPage from './pages/HistoryPage'
import SettingsPage from './pages/SettingsPage'
import Navigation from './Navigation'
import { Settings, History, Home } from 'lucide-react'

const MainWindow: React.FC = () => {
  const { currentPage, setCurrentPage } = useAppStore()

  const navigationItems = [
    { id: 'home' as const, label: 'Home', icon: Home },
    { id: 'history' as const, label: 'History', icon: History },
    { id: 'settings' as const, label: 'Settings', icon: Settings }
  ]

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage />
      case 'history':
        return <HistoryPage />
      case 'settings':
        return <SettingsPage />
      default:
        return <HomePage />
    }
  }

  return (
    <div className="flex h-full bg-white dark:bg-gray-900">
      {/* Sidebar Navigation */}
      <div className="w-64 bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <div className="p-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">ST</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                Screen Translator
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">v3.0.0</p>
            </div>
          </div>
        </div>

        <Navigation
          items={navigationItems}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-y-auto p-6">
          {renderCurrentPage()}
        </main>
      </div>
    </div>
  )
}

export default MainWindow