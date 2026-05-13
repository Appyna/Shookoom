'use client'

import Link from 'next/link'
import { Home, Grid3X3, Search } from 'lucide-react'

interface BottomNavProps {
  active: 'home' | 'categories' | 'search'
}

const NAV_ITEMS = [
  { id: 'home', href: '/', icon: Home, label: 'Accueil' },
  { id: 'categories', href: '/categories/1', icon: Grid3X3, label: 'Catégories' },
  { id: 'search', href: '/recherche', icon: Search, label: 'Recherche' },
]

export default function BottomNav({ active }: BottomNavProps) {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 flex items-center justify-around px-4 py-3 safe-area-pb"
      style={{
        background: 'white',
        boxShadow: '0 -4px 24px rgba(26,58,92,0.12)',
        borderTop: '1px solid rgba(26,58,92,0.06)',
        zIndex: 50
      }}
    >
      {NAV_ITEMS.map(item => {
        const isActive = item.id === active
        const Icon = item.icon
        return (
          <Link key={item.id} href={item.href}>
            <div className="flex flex-col items-center gap-1 px-4 py-1">
              <div
                className="w-10 h-10 rounded-2xl flex items-center justify-center transition-all"
                style={isActive ? { background: 'var(--navy-dark)' } : { background: 'transparent' }}
              >
                <Icon
                  size={20}
                  style={isActive ? { color: 'var(--teal-light)' } : { color: 'var(--gray-mid)' }}
                />
              </div>
              <span
                className="text-xs font-medium"
                style={isActive ? { color: 'var(--navy)' } : { color: 'var(--gray-mid)' }}
              >
                {item.label}
              </span>
            </div>
          </Link>
        )
      })}
    </nav>
  )
}
