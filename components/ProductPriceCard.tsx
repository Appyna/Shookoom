'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, Tag } from 'lucide-react'

interface Product {
  id: number
  name_fr: string
  name_he: string
  brand_fr?: string
  minPrice?: number
  maxPrice?: number
  cheapestChain?: string
  prices: Array<{
    chain_id: string
    price: number
    chains?: { name_fr: string }
  }>
}

export default function ProductPriceCard({ product }: { product: Product }) {
  const [expanded, setExpanded] = useState(false)

  const hasMultiplePrices = product.prices.length > 1
  const savings = product.maxPrice && product.minPrice 
    ? ((product.maxPrice - product.minPrice) / product.maxPrice * 100).toFixed(0)
    : null

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ background: 'white', boxShadow: '0 2px 12px rgba(26,58,92,0.08)' }}
    >
      {/* Main row */}
      <div
        className="p-4 flex items-center gap-3 cursor-pointer"
        onClick={() => hasMultiplePrices && setExpanded(!expanded)}
      >
        {/* Product icon placeholder */}
        <div className="w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
          style={{ background: 'var(--gray-soft)' }}>
          🏷️
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate" style={{ color: 'var(--navy)' }}>
            {product.name_fr || product.name_he}
          </p>
          {product.brand_fr && (
            <p className="text-xs mt-0.5" style={{ color: 'var(--gray-mid)' }}>
              {product.brand_fr}
            </p>
          )}
          {product.cheapestChain && (
            <p className="text-xs mt-1 font-medium" style={{ color: 'var(--teal)' }}>
              Moins cher : {product.cheapestChain}
            </p>
          )}
        </div>

        {/* Price + expand */}
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          {product.minPrice ? (
            <span className="text-base font-bold" style={{ color: 'var(--navy)' }}>
              ₪{product.minPrice.toFixed(2)}
            </span>
          ) : (
            <span className="text-xs" style={{ color: 'var(--gray-mid)' }}>N/A</span>
          )}
          
          {savings && parseInt(savings) > 5 && (
            <span className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ background: '#e0fff0', color: '#00875a' }}>
              -{savings}%
            </span>
          )}

          {hasMultiplePrices && (
            <div style={{ color: 'var(--gray-mid)' }}>
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          )}
        </div>
      </div>

      {/* Expanded prices */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--gray-soft)' }} className="px-4 pb-4 pt-3">
          <p className="text-xs font-semibold mb-3" style={{ color: 'var(--gray-mid)' }}>
            Prix par magasin
          </p>
          <div className="space-y-2">
            {product.prices.map((p, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {i === 0 && (
                    <div className="w-4 h-4 rounded-full flex items-center justify-center"
                      style={{ background: 'var(--teal)' }}>
                      <Tag size={8} className="text-white" />
                    </div>
                  )}
                  {i > 0 && <div className="w-4" />}
                  <span className="text-sm" style={{ color: 'var(--navy)' }}>
                    {p.chains?.name_fr || p.chain_id}
                  </span>
                </div>
                <span
                  className={`text-sm font-semibold ${i === 0 ? 'text-teal-600' : ''}`}
                  style={i === 0 ? { color: 'var(--teal)' } : { color: 'var(--navy)' }}
                >
                  ₪{p.price.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
