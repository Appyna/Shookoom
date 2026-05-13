'use client'

import { useState, useEffect } from 'react'
import { ArrowLeft, SlidersHorizontal } from 'lucide-react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import ProductPriceCard from '@/components/ProductPriceCard'
import BottomNav from '@/components/BottomNav'

const CATEGORY_INFO: Record<string, { name: string; icon: string; color: string }> = {
  '1': { name: 'Produits laitiers', icon: '🥛', color: '#e0f4ff' },
  '2': { name: 'Viandes & Volailles', icon: '🥩', color: '#ffe0e0' },
  '3': { name: 'Fruits & Légumes', icon: '🥦', color: '#e0ffe8' },
  '4': { name: 'Boulangerie', icon: '🍞', color: '#fff4e0' },
  '5': { name: 'Surgelés', icon: '❄️', color: '#e0eeff' },
  '6': { name: 'Boissons', icon: '🥤', color: '#f0e0ff' },
  '7': { name: 'Épicerie', icon: '🛒', color: '#e8e0d8' },
  '8': { name: 'Hygiène & Beauté', icon: '🧴', color: '#ffe0f4' },
  '9': { name: 'Nettoyage', icon: '🧹', color: '#e0fff8' },
  '10': { name: 'Bébé', icon: '👶', color: '#fffff0' },
}

export default function CategoryPage({ params }: { params: { id: string } }) {
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<'name' | 'price'>('name')
  
  const cat = CATEGORY_INFO[params.id] || { name: 'Catégorie', icon: '📦', color: '#f0f0f0' }

  useEffect(() => {
    async function loadProducts() {
      setLoading(true)
      
      const { data: productList } = await supabase
        .from('products')
        .select('id, barcode, name_fr, name_he, brand_fr')
        .eq('category_id', parseInt(params.id))
        .limit(50)

      if (!productList?.length) {
        setProducts([])
        setLoading(false)
        return
      }

      const productIds = productList.map(p => p.id)
      const { data: prices } = await supabase
        .from('prices')
        .select('product_id, price, chain_id, chains(name_fr)')
        .in('product_id', productIds)
        .order('price', { ascending: true })

      const pricesByProduct: Record<number, any[]> = {}
      prices?.forEach(p => {
        if (!pricesByProduct[p.product_id]) pricesByProduct[p.product_id] = []
        pricesByProduct[p.product_id].push(p)
      })

      const enriched = productList.map(p => ({
        ...p,
        prices: pricesByProduct[p.id] || [],
        minPrice: pricesByProduct[p.id]?.[0]?.price || null,
        cheapestChain: pricesByProduct[p.id]?.[0]?.chains?.name_fr || null,
      }))

      setProducts(enriched)
      setLoading(false)
    }

    loadProducts()
  }, [params.id])

  const sorted = [...products].sort((a, b) => {
    if (sortBy === 'price') return (a.minPrice || 999) - (b.minPrice || 999)
    return (a.name_fr || '').localeCompare(b.name_fr || '')
  })

  return (
    <div className="min-h-screen" style={{ background: 'var(--gray-soft)' }}>
      
      {/* Header */}
      <header style={{ background: 'var(--navy-dark)' }} className="px-5 pt-12 pb-5">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <Link href="/">
              <div className="w-8 h-8 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(255,255,255,0.1)' }}>
                <ArrowLeft size={16} className="text-white" />
              </div>
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base"
                style={{ background: cat.color }}>
                {cat.icon}
              </div>
              <span className="font-display font-bold text-white">{cat.name}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="px-5 py-6 max-w-lg mx-auto">
        
        {/* Sort bar */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs" style={{ color: 'var(--gray-mid)' }}>
            {products.length} produit{products.length > 1 ? 's' : ''}
          </p>
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={14} style={{ color: 'var(--gray-mid)' }} />
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              className="text-xs border-none bg-transparent outline-none cursor-pointer"
              style={{ color: 'var(--navy)' }}
            >
              <option value="name">A → Z</option>
              <option value="price">Prix croissant</option>
            </select>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="skeleton h-24 w-full" />
            ))}
          </div>
        )}

        {/* Empty */}
        {!loading && products.length === 0 && (
          <div className="text-center py-16">
            <div className="text-4xl mb-3">{cat.icon}</div>
            <p className="font-medium" style={{ color: 'var(--navy)' }}>
              Données en cours de chargement
            </p>
            <p className="text-sm mt-1" style={{ color: 'var(--gray-mid)' }}>
              Importez d'abord les données Kaggle
            </p>
          </div>
        )}

        {/* Products */}
        {!loading && sorted.length > 0 && (
          <div className="space-y-3">
            {sorted.map(product => (
              <ProductPriceCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </main>

      <BottomNav active="categories" />
    </div>
  )
}
