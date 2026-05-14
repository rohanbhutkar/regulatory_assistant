import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

interface NavItem {
  id: string
  label: string
  href: string
  icon?: React.ReactNode
  badge?: string | number
  children?: NavItem[]
}

interface ModernNavbarProps {
  items: NavItem[]
  logo?: React.ReactNode
  user?: {
    name: string
    avatar?: string
    email: string
  }
  onItemClick?: (item: NavItem) => void
  className?: string
}

export function ModernNavbar({
  items,
  logo,
  user,
  onItemClick,
  className
}: ModernNavbarProps) {
  const [activeItem, setActiveItem] = useState<string>('')
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  
  const handleItemClick = (item: NavItem) => {
    setActiveItem(item.id)
    onItemClick?.(item)
    setIsMobileMenuOpen(false)
  }
  
  return (
    <nav className={cn('bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50', className)}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            {logo || (
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">CK</span>
                </div>
                <span className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  Clinical Knowledge
                </span>
              </div>
            )}
          </div>
          
          {/* Desktop Navigation */}
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-4">
              {items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleItemClick(item)}
                  className={cn(
                    'px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-2',
                    activeItem === item.id
                      ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800'
                  )}
                >
                  {item.icon && <span>{item.icon}</span>}
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="bg-red-500 text-white text-xs rounded-full px-2 py-1 min-w-[20px] text-center">
                      {item.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
          
          {/* User Menu */}
          <div className="hidden md:block">
            <div className="ml-4 flex items-center md:ml-6">
              {user ? (
                <div className="flex items-center space-x-3">
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {user.name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {user.email}
                    </p>
                  </div>
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                    {user.avatar ? (
                      <img
                        src={user.avatar}
                        alt={user.name}
                        className="w-8 h-8 rounded-full"
                      />
                    ) : (
                      <span className="text-white text-sm font-medium">
                        {user.name.charAt(0).toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <Button variant="default" size="sm">
                  Sign In
                </Button>
              )}
            </div>
          </div>
          
          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
            >
              <span className="sr-only">Open main menu</span>
              {isMobileMenuOpen ? (
                <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
      
      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => handleItemClick(item)}
                className={cn(
                  'w-full text-left px-3 py-2 rounded-md text-base font-medium transition-all duration-200 flex items-center justify-between',
                  activeItem === item.id
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                <div className="flex items-center space-x-2">
                  {item.icon && <span>{item.icon}</span>}
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="bg-red-500 text-white text-xs rounded-full px-2 py-1 min-w-[20px] text-center">
                    {item.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </nav>
  )
}

interface SidebarProps {
  items: NavItem[]
  isOpen: boolean
  onClose: () => void
  className?: string
}

export function ModernSidebar({
  items,
  isOpen,
  onClose,
  className
}: SidebarProps) {
  const [activeItem, setActiveItem] = useState<string>('')
  
  const handleItemClick = (item: NavItem) => {
    setActiveItem(item.id)
  }
  
  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
          className
        )}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">CK</span>
              </div>
              <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Clinical Knowledge
              </span>
            </div>
            <button
              onClick={onClose}
              className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto scrollbar-modern">
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => handleItemClick(item)}
                className={cn(
                  'w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                  activeItem === item.id
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                <div className="flex items-center space-x-3">
                  {item.icon && <span>{item.icon}</span>}
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="bg-red-500 text-white text-xs rounded-full px-2 py-1 min-w-[20px] text-center">
                    {item.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>
    </>
  )
}
