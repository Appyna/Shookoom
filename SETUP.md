# 🚀 Guide d'installation Shookoom — Pas à pas

---

## ÉTAPE 1 : Créer le projet sur GitHub

1. Va sur https://github.com → "New repository"
2. Nom : `shookoom`
3. Privé ou public → ton choix
4. Clique "Create repository"

---

## ÉTAPE 2 : Préparer les tables Supabase

1. Va sur https://supabase.com → ton projet **Shookoom**
2. Dans le menu gauche → **SQL Editor**
3. Colle tout le contenu du fichier `supabase/schema.sql`
4. Clique **Run**
5. Tu devrais voir "Success" → les tables sont créées

---

## ÉTAPE 3 : Ouvrir le projet dans Cursor

1. Télécharge et ouvre **Cursor** (https://cursor.com)
2. Ouvre le dossier `shookoom` que tu as récupéré
3. Ouvre un terminal dans Cursor : `Ctrl + ~`

---

## ÉTAPE 4 : Installer les dépendances

Dans le terminal Cursor, tape :

```bash
npm install
```

Attends que tout s'installe (2-3 minutes).

---

## ÉTAPE 5 : Configurer les variables d'environnement

1. Copie le fichier `.env.example` et renomme-le `.env.local`
2. Remplis les valeurs :

```
NEXT_PUBLIC_SUPABASE_URL=https://iwqaichmldpsutfujoco.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...  (ta clé)
ANTHROPIC_API_KEY=sk-ant-...  (à créer sur console.anthropic.com)
KAGGLE_USERNAME=...  (ton username Kaggle)
KAGGLE_KEY=...  (à créer sur kaggle.com/settings → API)
```

**Où trouver la clé Anthropic :**
→ https://console.anthropic.com → API Keys → Create Key

**Où trouver la clé Kaggle :**
→ https://www.kaggle.com → Settings → API → Create New Token

---

## ÉTAPE 6 : Tester l'app localement

```bash
npm run dev
```

Ouvre http://localhost:3000 — tu devrais voir l'app Shookoom !

(Sans données importées, les catégories seront vides — c'est normal)

---

## ÉTAPE 7 : Importer les données Kaggle (IMPORTANT)

1. Va sur : https://www.kaggle.com/datasets/erlichsefi/israeli-supermarkets-2024
2. Clique "Download" → télécharge le ZIP
3. Décompresse dans le dossier `scripts/kaggle_data/`
4. Dans le terminal :

```bash
cd scripts
pip install -r requirements.txt
python import_kaggle.py
```

⏳ L'import prend 20-40 minutes (traduction IA de tous les produits)
✅ Une fois terminé, l'app affiche tous les prix en français !

---

## ÉTAPE 8 : Déployer sur Vercel

1. Va sur https://vercel.com → "Add New Project"
2. Importe ton repo GitHub `shookoom`
3. Dans "Environment Variables", ajoute :
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Clique **Deploy**
5. En 2 minutes, ton app est en ligne ! 🎉

---

## ÉTAPE 9 : Automatiser l'import quotidien

1. Va sur GitHub → ton repo `shookoom`
2. Settings → Secrets and variables → Actions
3. Ajoute ces secrets :
   - `SUPABASE_SERVICE_KEY` (dans Supabase → Settings → API → service_role key)
   - `ANTHROPIC_API_KEY`
   - `KAGGLE_USERNAME`
   - `KAGGLE_KEY`
4. Le workflow `.github/workflows/daily_import.yml` se lancera automatiquement chaque jour à 6h (heure israélienne)

---

## ✅ Résumé des coûts

| Service | Coût |
|---------|------|
| Supabase Pro | 25€/mois |
| Vercel | Gratuit |
| GitHub Actions | Gratuit |
| Claude (traduction, 1 seule fois) | ~2-5€ |
| **TOTAL** | **~25-30€/mois** |

---

## ❓ Problèmes fréquents

**"Module not found"** → Lance `npm install` dans le terminal

**"Supabase error"** → Vérifie que le schema.sql a bien été exécuté

**"No data"** → Lance l'import Kaggle (étape 7)

**Traduction trop lente** → Normal, ~3000 produits × 50ms = 2-3 min par chaîne
