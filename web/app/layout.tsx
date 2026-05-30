import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Dret Local Cerdanya',
  description: 'Xat de consulta sobre legislacio local de la Cerdanya.',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ca">
      <body>{children}</body>
    </html>
  )
}
