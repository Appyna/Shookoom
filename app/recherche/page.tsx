'use client'

import { useState, useEffect, useCallback } from 'react'
import { Search, ArrowLeft, X } from 'lucide-react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import ProductPriceCard from '@/components/ProductPriceCard'
import BottomNav from '@/components/BottomNav'

export default function RecherchePage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const search = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([])
      return
    }
    setLoading(true)
    
    try {
      // Récupérer les produits correspondants
      const { data: products, error } = await supabase
        .from('products')
        .select('id, barcode, name_fr, name_he, brand_fr, category_id')
        .ilike('name_fr', `%${q}%`)
        .limit(20)

      if (error) throw error
      if (!products?.length) {
        setResults([])
        setLoading(false)
        return
      }

      // Récupérer les prix pour ces produits
      const productIds = products.map(p => p.id)
      const { data: prices } = await supabase
        .from('prices')
        .select('product_id, price, chain_id, chains(name_fr)')
        .in('product_id', productIds)
        .order('price', { ascending: true })

      // Grouper les prix par produit
      const pricesByProduct: Record<number, any[]> = {}
      prices?.forEach(p => {
        if (!pricesByProduct[p.product_id]) pricesByProduct[p.product_id] = []
        pricesByProduct[p.product_id].push(p)
      })

      const enriched = products.map(p => ({
        ...p,
        prices: pricesByProduct[p.id] || [],
        minPrice: pricesByProduct[p.id]?.[0]?.price || null,
        maxPrice: pricesByProduct[p.id]?.[pricesByProduct[p.id]?.length - 1]?.price || null,
        cheapestChain: pricesByProduct[p.id]?.[0]?.chains?.name_fr || null,
      }))

      setResults(enriched)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => search(query), 300)
    return () => clearTimeout(timer)
  }, [query, search])

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
            <span className="font-display font-bold text-white">Recherche</span>
          </div>

          {/* Search input */}
          <div className="flex items-center gap-3 px-4 py-3 rounded-2xl"
            style={{ background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.2)' }}>
            <Search size={18} style={{ color: 'var(--teal-light)' }} />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Lait, pain, poulet..."
              autoFocus
              className="flex-1 bg-transparent text-white placeholder-white/40 text-sm outline-none"
            />
            {query && (
              <button onClick={() => setQuery('')}>
                <X size={16} className="text-white/50" />
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="px-5 py-6 max-w-lg mx-auto">
        
        {/* Loading skeletons */}
        {loading && (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skeleton h-24 w-full" />
            ))}
          </div>
        )}

        {/* No results */}
        {!loading && query.length >= 2 && results.length === 0 && (
          <div className="text-center py-16">
            <div className="text-4xl mb-3">🔍</div>
            <p className="font-medium" style={{ color: 'var(--navy)' }}>Aucun résultat</p>
            <p className="text-sm mt-1" style={{ color: 'var(--gray-mid)' }}>
              Essayez un autre terme
            </p>
          </div>
        )}

        {/* Empty state */}
        {!loading && query.length < 2 && (
          <div className="text-center py-16">
            <div className="text-4xl mb-3">🛒</div>
            <p className="font-medium" style={{ color: 'var(--navy)' }}>
              Cherchez un produit
            </p>
            <p className="text-sm mt-1" style={{ color: 'var(--gray-mid)' }}>
              Tapez au moins 2 caractères
            </p>
          </div>
        )}

        {/* Results */}
        {!loading && results.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs font-medium" style={{ color: 'var(--gray-mid)' }}>
              {results.length} produit{results.length > 1 ? 's' : ''} trouvé{results.length > 1 ? 's' : ''}
            </p>
            {results.map(product => (
              <ProductPriceCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </main>

      <BottomNav active="search" />
    </div>
  )
}
