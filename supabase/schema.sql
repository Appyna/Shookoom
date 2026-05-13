-- ============================================
-- SCHEMA SHOOKOOM v2 — Comparateur de prix
-- À exécuter dans Supabase SQL Editor
-- ============================================

-- Chaînes (id = slug kaggle ex: "rami_levy")
CREATE TABLE IF NOT EXISTS chains (
  id       TEXT PRIMARY KEY,   -- slug Kaggle (rami_levy, shufersal…)
  name_fr  TEXT NOT NULL,
  name_he  TEXT,
  logo_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Magasins
CREATE TABLE IF NOT EXISTS stores (
  id        TEXT PRIMARY KEY,  -- "{chain_slug}_{store_number}"
  chain_id  TEXT REFERENCES chains(id),
  city_fr   TEXT,
  city_he   TEXT,
  address   TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Catégories
CREATE TABLE IF NOT EXISTS categories (
  id      SERIAL PRIMARY KEY,
  name_fr TEXT NOT NULL,
  name_he TEXT,
  icon    TEXT,
  color   TEXT
);

-- Produits (barcode = clé unique internationale)
CREATE TABLE IF NOT EXISTS products (
  id            SERIAL PRIMARY KEY,
  barcode       TEXT UNIQUE NOT NULL,
  name_fr       TEXT,
  name_he       TEXT NOT NULL,
  brand_fr      TEXT,
  category_id   INTEGER REFERENCES categories(id),
  image_url     TEXT,
  unit          TEXT,
  translated_at TIMESTAMP,
  created_at    TIMESTAMP DEFAULT NOW()
);

-- Prix par chaîne/magasin
CREATE TABLE IF NOT EXISTS prices (
  id               SERIAL PRIMARY KEY,
  product_id       INTEGER REFERENCES products(id),
  chain_id         TEXT REFERENCES chains(id),
  store_id         TEXT REFERENCES stores(id),
  price            DECIMAL(10,2) NOT NULL,
  price_updated_at TIMESTAMP,
  imported_at      TIMESTAMP DEFAULT NOW()
);

-- Index performance
CREATE INDEX IF NOT EXISTS idx_prices_product  ON prices(product_id);
CREATE INDEX IF NOT EXISTS idx_prices_chain    ON prices(chain_id);
CREATE INDEX IF NOT EXISTS idx_products_bc     ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_products_cat    ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_search ON products USING gin(
  to_tsvector('simple', COALESCE(name_fr,'') || ' ' || COALESCE(name_he,''))
);

-- Vue principale : produit + meilleur prix par chaîne
CREATE OR REPLACE VIEW product_prices AS
SELECT
  p.id            AS product_id,
  p.barcode,
  p.name_fr,
  p.name_he,
  p.brand_fr,
  p.category_id,
  c2.name_fr      AS category_name,
  pr.price,
  pr.price_updated_at,
  ch.id           AS chain_id,
  ch.name_fr      AS chain_name,
  pr.store_id
FROM products p
JOIN prices  pr ON pr.product_id = p.id
JOIN chains  ch ON ch.id = pr.chain_id
LEFT JOIN categories c2 ON c2.id = p.category_id;

-- Catégories de base
INSERT INTO categories (id, name_fr, name_he, icon, color) VALUES
  (1,  'Produits laitiers',  'מוצרי חלב',           '🥛', '#e0f4ff'),
  (2,  'Viandes & Volailles','בשר ועוף',             '🥩', '#ffe0e0'),
  (3,  'Fruits & Légumes',   'פירות וירקות',          '🥦', '#e0ffe8'),
  (4,  'Boulangerie',        'לחם ומאפים',            '🍞', '#fff4e0'),
  (5,  'Surgelés',           'מוצרים קפואים',         '❄️', '#e0eeff'),
  (6,  'Boissons',           'משקאות',               '🥤', '#f0e0ff'),
  (7,  'Épicerie',           'מכולת',                '🛒', '#e8e0d8'),
  (8,  'Hygiène & Beauté',   'היגיינה וקוסמטיקה',     '🧴', '#ffe0f4'),
  (9,  'Nettoyage',          'ניקיון',               '🧹', '#e0fff8'),
  (10, 'Bébé',              'תינוקות',              '👶', '#fffff0')
ON CONFLICT (id) DO NOTHING;

-- RLS : lecture publique, écriture service_role uniquement
ALTER TABLE chains     ENABLE ROW LEVEL SECURITY;
ALTER TABLE products   ENABLE ROW LEVEL SECURITY;
ALTER TABLE prices     ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Lecture publique chains"     ON chains     FOR SELECT USING (true);
CREATE POLICY "Lecture publique products"   ON products   FOR SELECT USING (true);
CREATE POLICY "Lecture publique prices"     ON prices     FOR SELECT USING (true);
CREATE POLICY "Lecture publique categories" ON categories FOR SELECT USING (true);
