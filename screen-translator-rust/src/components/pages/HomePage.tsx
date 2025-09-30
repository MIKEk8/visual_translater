import React from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '../../store/appStore'
import {
  Zap,
  Camera,
  Clipboard,
  History,
  Settings,
  Sparkles,
  Globe,
  Cpu
} from 'lucide-react'

const HomePage: React.FC = () => {
  const {
    getRecentTranslations,
    setShowAreaSelector,
    setCurrentPage,
    config
  } = useAppStore()

  const recentTranslations = getRecentTranslations(3)

  const quickActions = [
    {
      id: 'screenshot',
      title: 'Screenshot Area',
      description: 'Select screen area for translation',
      icon: Camera,
      color: 'blue',
      action: () => setShowAreaSelector(true)
    },
    {
      id: 'clipboard',
      title: 'Clipboard Translation',
      description: 'Translate clipboard content',
      icon: Clipboard,
      color: 'green',
      action: () => {
        // TODO: Implement clipboard translation
        console.log('Clipboard translation')
      }
    },
    {
      id: 'history',
      title: 'View History',
      description: 'Browse translation history',
      icon: History,
      color: 'purple',
      action: () => setCurrentPage('history')
    },
    {
      id: 'settings',
      title: 'Settings',
      description: 'Configure application',
      icon: Settings,
      color: 'gray',
      action: () => setCurrentPage('settings')
    }
  ]

  const features = [
    {
      icon: Zap,
      title: 'Intelligent Hotkeys',
      description: 'Alt+A with time-based detection for quick/long press actions'
    },
    {
      icon: Sparkles,
      title: 'AI-Enhanced OCR',
      description: 'Advanced text recognition with preprocessing and context detection'
    },
    {
      icon: Globe,
      title: 'Multi-Language Support',
      description: 'Support for 7+ languages with auto-detection'
    },
    {
      icon: Cpu,
      title: 'Rust Performance',
      description: 'Lightning-fast processing with memory safety'
    }
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Welcome to Screen Translator v3.0
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Advanced screen translation with AI-powered OCR and intelligent hotkeys
        </p>
      </motion.div>

      {/* Quick Actions */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action, index) => (
            <motion.button
              key={action.id}
              onClick={action.action}
              className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200 group"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className={`w-12 h-12 bg-${action.color}-100 dark:bg-${action.color}-900/30 rounded-lg flex items-center justify-center mb-3 group-hover:bg-${action.color}-200 dark:group-hover:bg-${action.color}-900/50 transition-colors`}>
                <action.icon className={`w-6 h-6 text-${action.color}-600 dark:text-${action.color}-400`} />
              </div>
              <h3 className="font-medium text-gray-900 dark:text-white text-sm mb-1">
                {action.title}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {action.description}
              </p>
            </motion.button>
          ))}
        </div>
      </motion.section>

      {/* Recent Translations */}
      {recentTranslations.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Recent Translations
            </h2>
            <button
              onClick={() => setCurrentPage('history')}
              className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
            >
              View all
            </button>
          </div>
          <div className="space-y-3">
            {recentTranslations.map((translation, index) => (
              <motion.div
                key={translation.id}
                className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                      {translation.originalText}
                    </p>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {translation.translatedText}
                    </p>
                  </div>
                  <div className="ml-4 text-right">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {translation.sourceLang.toUpperCase()} → {translation.targetLang.toUpperCase()}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {translation.timestamp.toLocaleDateString()}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.section>
      )}

      {/* Features Overview */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Key Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="flex items-start space-x-3">
                <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                  <feature.icon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {feature.description}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* Current Configuration */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6"
      >
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Current Configuration
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400">Quick Translate:</span>
            <div className="font-medium text-gray-900 dark:text-white">
              {config?.hotkeys.quickTranslate || 'Alt+A'}
            </div>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">OCR Language:</span>
            <div className="font-medium text-gray-900 dark:text-white">
              {config?.ocr.language || 'English'}
            </div>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Target Language:</span>
            <div className="font-medium text-gray-900 dark:text-white">
              {config?.translation.targetLang || 'English'}
            </div>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Theme:</span>
            <div className="font-medium text-gray-900 dark:text-white">
              {config?.ui.theme || 'Dark'}
            </div>
          </div>
        </div>
      </motion.section>
    </div>
  )
}

export default HomePage