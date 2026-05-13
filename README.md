# Shookoom 🛒
Comparateur de prix alimentaires pour francophones en Israël

## Stack
- **Frontend**: Next.js 14 + Tailwind CSS
- **Backend**: Supabase (PostgreSQL)
- **Données**: Kaggle Israeli Supermarkets dataset
- **Traduction**: Claude API (hébreu → français)
- **Déploiement**: Vercel

## Setup rapide

### 1. Installe les dépendances
```bash
npm install
```

### 2. Configure les variables d'environnement
Copie `.env.example` en `.env.local` et remplis les valeurs.

### 3. Crée les tables Supabase
Exécute le fichier `supabase/schema.sql` dans le SQL Editor de Supabase.

### 4. Importe les données Kaggle
```bash
cd scripts
pip install -r requirements.txt
python import_kaggle.py
```

### 5. Lance l'app
```bash
npm run dev
```
