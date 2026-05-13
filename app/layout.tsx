import type { Metadata } from 'next'
import { Outfit, Syne } from 'next/font/google'
import './globals.css'

const outfit = Outfit({ 
  subsets: ['latin'],
  variable: '--font-outfit',
  weight: ['300', '400', '500', '600', '700']
})

const syne = Syne({ 
  subsets: ['latin'],
  variable: '--font-syne',
  weight: ['600', '700', '800']
})

export const metadata: Metadata = {
  title: 'Shookoom – Comparez les prix en Israël',
  description: 'Trouvez les meilleurs prix pour vos courses dans tous les supermarchés israéliens.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr">
      <body className={`${outfit.variable} ${syne.variable} font-sans`}>
        {children}
      </body>
    </html>
  )
}
