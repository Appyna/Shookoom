'use client'

import { useState } from 'react'
import { Search, TrendingDown, MapPin } from 'lucide-react'
import Link from 'next/link'
import BottomNav from '@/components/BottomNav'

const CATEGORIES = [
  { id: 1, name: 'Produits laitiers', icon: '🥛', color: '#e0f4ff' },
  { id: 2, name: 'Viandes', icon: '🥩', color: '#ffe0e0' },
  { id: 3, name: 'Fruits & Légumes', icon: '🥦', color: '#e0ffe8' },
  { id: 4, name: 'Boulangerie', icon: '🍞', color: '#fff4e0' },
  { id: 5, name: 'Surgelés', icon: '❄️', color: '#e0eeff' },
  { id: 6, name: 'Boissons', icon: '🥤', color: '#f0e0ff' },
  { id: 7, name: 'Épicerie', icon: '🛒', color: '#e8e0d8' },
  { id: 8, name: 'Hygiène', icon: '🧴', color: '#ffe0f4' },
  { id: 9, name: 'Nettoyage', icon: '🧹', color: '#e0fff8' },
  { id: 10, name: 'Bébé', icon: '👶', color: '#fffff0' },
]

export default function HomePage() {
  const [search, setSearch] = useState('')

  return (
    <div className="min-h-screen" style={{ background: 'var(--gray-soft)' }}>
      
      {/* Header */}
      <header style={{ background: 'var(--navy-dark)' }} className="px-5 pt-12 pb-8">
        <div className="max-w-lg mx-auto">
          
          {/* Logo */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
              style={{ background: 'var(--teal)' }}>
              🛒
            </div>
            <span className="font-display text-xl font-bold text-white tracking-tight">
              Shookoom
            </span>
          </div>

          {/* Tagline */}
          <h1 className="font-display text-2xl font-bold text-white mb-1 leading-tight">
            Les meilleurs prix<br/>
            <span style={{ color: 'var(--teal-light)' }}>en Israël</span>
          </h1>
          <p className="text-sm mb-5" style={{ color: 'var(--gray-mid)' }}>
            Comparez les prix dans tous les supermarchés
          </p>

          {/* Search bar */}
          <Link href="/recherche">
            <div className="flex items-center gap-3 px-4 py-3 rounded-2xl cursor-pointer"
              style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)' }}>
              <Search size={18} style={{ color: 'var(--teal-light)' }} />
              <span className="text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>
                Rechercher un produit...
              </span>
            </div>
          </Link>
        </div>
      </header>

      {/* Stats strip */}
      <div style={{ background: 'var(--teal)' }} className="px-5 py-3">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2 text-white text-xs font-medium">
            <TrendingDown size={14} />
            <span>Économisez jusqu'à 35% sur vos courses</span>
          </div>
          <div className="flex items-center gap-1 text-xs text-white opacity-80">
            <MapPin size={12} />
            <span>33 chaînes</span>
          </div>
        </div>
      </div>

      {/* Categories */}
      <main className="px-5 py-6 max-w-lg mx-auto">
        <h2 className="font-display text-base font-bold mb-4" style={{ color: 'var(--navy)' }}>
          Catégories
        </h2>
        
        <div className="grid grid-cols-2 gap-3">
          {CATEGORIES.map((cat, i) => (
            <Link key={cat.id} href={`/categories/${cat.id}`}>
              <div
                className="rounded-2xl p-4 flex items-center gap-3 cursor-pointer hover:scale-[1.02] transition-transform active:scale-[0.98]"
                style={{ 
                  background: 'white',
                  boxShadow: '0 2px 12px rgba(26,58,92,0.08)',
                  animationDelay: `${i * 40}ms`
                }}
              >
                <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
                  style={{ background: cat.color }}>
                  {cat.icon}
                </div>
                <span className="text-sm font-medium leading-tight" style={{ color: 'var(--navy)' }}>
                  {cat.name}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </main>

      <BottomNav active="home" />
    </div>
  )
}
