import React from 'react'
import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'

interface NavigationItem {
  id: 'home' | 'history' | 'settings'
  label: string
  icon: LucideIcon
}

interface NavigationProps {
  items: NavigationItem[]
  currentPage: 'home' | 'history' | 'settings'
  onPageChange: (page: 'home' | 'history' | 'settings') => void
}

const Navigation: React.FC<NavigationProps> = ({ items, currentPage, onPageChange }) => {
  return (
    <nav className="px-3">
      <ul className="space-y-1">
        {items.map((item) => {
          const isActive = currentPage === item.id
          return (
            <li key={item.id}>
              <button
                onClick={() => onPageChange(item.id)}
                className={`relative w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute inset-0 bg-blue-100 dark:bg-blue-900/30 rounded-lg"
                    transition={{ type: "spring", duration: 0.3 }}
                  />
                )}
                <item.icon className={`relative z-10 w-5 h-5 ${
                  isActive ? 'text-blue-600 dark:text-blue-400' : ''
                }`} />
                <span className="relative z-10">{item.label}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export default Navigation