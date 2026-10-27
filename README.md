# EONE-Test — Tests psychométriques

Application légère et autonome, extraite du module « Tests psychométriques » d'ENOSISAPP
(`recrutement-service`). Un seul utilisateur : **l'administrateur**. Aucune dépendance à la
CVthèque, aux recruteurs ou à l'authentification Azure.

## Fonctionnalités

**1. Tests psychométriques**
- L'admin saisit **prénom, nom, email** puis clique sur **« Générer le test »** :
  une version est tirée au hasard pour chaque core value.
- **Copier le lien** : crée le lien personnel du candidat (valable 7 jours) et le copie ;
  l'admin le transmet lui-même (Outlook, WhatsApp…). **L'application n'envoie aucun email.**
  **Prolonger** : même lien, validité repoussée de 7 jours (tant que le test n'a pas commencé).
- Le candidat ouvre `/passer-test?token=…` (aucune connexion requise) et dispose de
  **15 minutes**, sans retour en arrière. Le test se clôture automatiquement à la fin du temps.
- **Voir les résultats** : score global pondéré, vue radar par core value et détail des réponses.
- Statuts : `À envoyer` → `Envoyé` (lien créé) → `En cours` → `Répondu`.

**2. Banque de questions**
- Core values → versions → questions (pondération) → réponses (pourcentage 0–100).
- Ajouter, modifier ou supprimer à chaque niveau. Chaque élément affiche qui l'a modifié en dernier, et quand.
- Une réponse ou une version déjà utilisée dans un test ne peut pas être supprimée
  (il faut d'abord supprimer le test).
- Une core value sans version bloque la génération des tests.

**Calcul du score** (jamais stocké, recalculé à chaque affichage) :
`Σ(pourcentage de la réponse choisie × pondération) / Σ pondération`.
Une question sans réponse compte 0 mais garde sa pondération.

## Structure

```
EONE-Test/
├── backend/                 Django 5 + DRF, PostgreSQL 16
│   ├── eone_test/           settings, urls
│   └── app/
│       ├── models/          CoreValue, Version, Question, Answer, Test, TestVersion, TestVersionAnswer
│       ├── services/        question_bank_service, test_service, test_candidat_service
│       ├── views/           auth, banque de questions, tests (admin), test-candidat (public)
│       ├── management/commands/
│       │   ├── seed_core_values_bank.py   (+ data/banque_questions_enosis.json)
│       │   └── ensure_admin.py
│       └── tests/
├── frontend/                React 18 + Vite + axios — mêmes composants et styles qu'ENOSISAPP
│   └── src/
│       ├── styles.css, tokens/, atoms/, molecules/, organisms/, templates/   (copiés d'ENOSISAPP)
│       ├── LoginPage.jsx, Dashboard.jsx, App.jsx                             (spécifiques à EONE-Test)
│       ├── pages/TestsPsychometriques/   TestsPsychometriquesPage, TestResultsDialog, BanqueQuestionsPage
│       └── CandidatTestPage.jsx          (identique à ENOSISAPP)
└── docker-compose.yml
```

## Démarrage en local (développement)

**Base de données** : PostgreSQL 16 dans son propre conteneur, publié sur `127.0.0.1:5433`
(sans conflit avec le Postgres d'ENOSISAPP) :
```powershell
Copy-Item backend\.env.example backend\.env   # puis modifiez ADMIN_PASSWORD et POSTGRES_PASSWORD
docker compose up -d postgres
```

**Backend** (port 8000) :
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_core_values_bank   # 5 core values, 25 versions, 150 questions
.\.venv\Scripts\python manage.py ensure_admin
.\.venv\Scripts\python manage.py runserver 8000
```

**Frontend** (port 5173, `/api` est redirigé vers le port 8000) :
```powershell
cd frontend
npm install
npm run dev
```

Ouvrez http://localhost:5173 et connectez-vous avec `ADMIN_USERNAME` / `ADMIN_PASSWORD`.


**Tests automatisés :**
```powershell
cd backend
.\.venv\Scripts\python manage.py test app
```

## Démarrage avec Docker (local)

```powershell
Copy-Item backend\.env.example backend\.env   # définissez ADMIN_PASSWORD, POSTGRES_PASSWORD
docker compose up -d --build
```
L'application est disponible sur http://localhost:8080. Au démarrage, le backend attend que
Postgres soit prêt, applique les migrations, charge la banque de questions (idempotent) et crée
le compte admin. Les données sont conservées dans le volume `postgres-data`.

Le mot de passe Postgres n'est appliqué qu'à la **première** création du volume. Pour le changer
ensuite, utilisez `ALTER USER` dans Postgres, ou supprimez le volume (`docker compose down -v`),
ce qui **efface toutes les données**.

## Déploiement sur un serveur (Oracle Cloud, HTTPS gratuit sur l'IP publique)

Le service `caddy` (activé par `--profile https`) se place devant l'application, obtient
automatiquement un certificat **Let's Encrypt gratuit pour l'IP publique** et le renouvelle seul.
Les certificats pour une IP durent environ 6 jours (profil `shortlived`), d'où le renouvellement
automatique. HTTP est redirigé vers HTTPS. Le frontend et Postgres ne sont accessibles que
depuis le serveur lui-même : le public passe forcément par Caddy.

**1. Ouvrir les ports 80 et 443 (les deux sont nécessaires : le port 80 sert à la validation Let's Encrypt).**
- **Console Oracle Cloud** : *Networking → Virtual Cloud Networks → (votre VCN) → Security Lists*
  (ou le *Network Security Group* de l'instance) → *Add Ingress Rules* :
  source `0.0.0.0/0`, protocole TCP, port de destination `80`, puis la même règle pour `443`.
- **Pare-feu de la machine** : les images Oracle bloquent aussi ces ports par défaut.
  - Ubuntu :
    ```bash
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
    sudo netfilter-persistent save
    ```
  - Oracle Linux :
    ```bash
    sudo firewall-cmd --permanent --add-service=http --add-service=https && sudo firewall-cmd --reload
    ```

**2. Installer Docker** (Ubuntu) : `curl -fsSL https://get.docker.com | sudo sh`, puis
`sudo usermod -aG docker $USER` et reconnectez-vous. Les instances ARM (Ampere) sont compatibles.

**3. Copier le projet** sur le serveur (sans `.venv`, `node_modules`, `dist`, `backups`, `backend/.env`),
par exemple dans `/opt/eone-test`.

**4. Configurer `backend/.env`** à partir de `backend/.env.example` (valeurs marquées « SERVEUR ») :
```ini
DEBUG=False
SECRET_KEY=<python3 -c "import secrets; print(secrets.token_urlsafe(50))">
ALLOWED_HOSTS=localhost,127.0.0.1,backend,<IP_PUBLIQUE>
SITE_ADDRESS=<IP_PUBLIQUE>
ACME_PROFILE=shortlived
FRONTEND_URL=https://<IP_PUBLIQUE>
POSTGRES_PASSWORD=<mot de passe fort>
ADMIN_PASSWORD=<mot de passe fort>
```

**5. Démarrer :**
```bash
docker compose --profile https up -d --build
docker compose logs -f caddy      # attendre « certificate obtained successfully »
```
L'application est alors disponible sur `https://<IP_PUBLIQUE>`.

**6. Sauvegardes quotidiennes** (gardées 14 jours dans `backups/`) :
```bash
chmod +x scripts/backup.sh
crontab -e
# ajouter :
0 2 * * * cd /opt/eone-test && ./scripts/backup.sh >> backups/backup.log 2>&1
```
Restauration : voir l'en-tête de [scripts/backup.sh](scripts/backup.sh). Copiez aussi
régulièrement le dossier `backups/` hors du serveur.

**Mise à jour de l'application** : recopiez le code, puis relancez la commande de l'étape 5.
Les données (volume `postgres-data`) et les certificats (volume `caddy-data`) sont conservés.

**Si vous obtenez un nom de domaine plus tard** (ex. `tests.enosis.ma`) : mettez-le dans
`SITE_ADDRESS`, `FRONTEND_URL` et `ALLOWED_HOSTS`, passez `ACME_PROFILE=classic`, puis relancez.

**Sécurité intégrée :**
- Les connexions admin expirent après `TOKEN_TTL_HOURS` (12 h par défaut).
- La connexion est limitée à 10 tentatives par minute et par IP ; l'IP réelle est lue derrière Caddy et nginx.
- Le passage du test (lien candidat) est limité à 60 requêtes par minute et par IP. Les compteurs
  sont stockés dans Postgres, donc partagés par tous les workers.
- **Pas de retour en arrière, imposé par le serveur** : seule la question en cours est envoyée au
  navigateur et peut recevoir une réponse. « Suivant » la valide définitivement, et les questions
  suivantes ne sont jamais envoyées à l'avance.
- Le chrono est contrôlé par le serveur, avec une marge réseau de 15 secondes.
- En-têtes HTTPS stricts : HSTS, Content-Security-Policy (scripts limités à l'application), anti-iframe,
  et le lien du candidat ne fuit pas vers d'autres sites. Voir [caddy/security-headers.caddy](caddy/security-headers.caddy).

Pour changer le mot de passe admin :
`docker compose exec backend python manage.py ensure_admin --password "NouveauMotDePasse" --reset-password`

## API

| Méthode | URL | Accès |
|---|---|---|
| POST | `/api/auth/login/` · `/api/auth/logout/` · GET `/api/auth/me/` | — / admin |
| CRUD | `/api/core-values/`, `/api/core-value-versions/?core_value_id=`, `/api/core-value-questions/?version_id=`, `/api/core-value-answers/?question_id=` | admin |
| GET / POST | `/api/tests-psychometriques/` (POST `{prenom, nom, email}` = générer) | admin |
| GET / DELETE | `/api/tests-psychometriques/{id}/` (détail + résultats) | admin |
| POST | `/api/tests-psychometriques/{id}/lien/` (créer le lien) · `.../prolonger/` (+7 jours) | admin |

Les appels admin portent l'en-tête `Authorization: Bearer <jeton>` (jeton renvoyé par `/api/auth/login/`).
| GET | `/api/test-candidat/{token}/` | public (jeton) |
| POST | `/api/test-candidat/{token}/demarrer/` · `repondre/` `{answer_id}` (question en cours) · `suivant/` (valide et avance) · `terminer/` | public (jeton) |

## Différences avec ENOSISAPP

- Le candidat est saisi directement (prénom, nom, email) : pas de lien avec la CVthèque,
  pas de validation recruteur, pas de catégories (Commercial, Cadre, Usine).
- Authentification : compte admin Django avec jeton DRF, à la place de JWT/Azure AD.
- Base PostgreSQL dédiée (`eone_test`), séparée de celle d'ENOSISAPP. Les données de tests
  existantes dans ENOSISAPP n'ont pas été migrées.
- Pas d'envoi d'email : l'admin copie le lien et le transmet lui-même au candidat.
- Questions et réponses gardent un ordre d'affichage stable (champ `created_at`).
  L'ordre A/B/C/D vu par le candidat est donc toujours l'ordre de saisie.
- Ajouts : suppression d'un test et bouton « Copier le lien ».
