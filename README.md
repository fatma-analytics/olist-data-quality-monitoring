# Monitoring BI et qualité des données

**Créatrice : Fatma Hammami**

Un pipeline de contrôle qualité transforme les fichiers e-commerce d’Olist en indicateurs de suivi exploitables dans Power BI. Il profile les tables, mesure la complétude et la cohérence, signale les anomalies et conserve les résultats d’exécution dans des fichiers tabulaires prêts à charger.

Le cas d’usage porte sur un point concret : une équipe BI doit pouvoir repérer rapidement les tables et les règles qui dégradent la fiabilité des indicateurs avant leur consommation dans les rapports.

## Jeu de données

Le projet utilise le [Brazilian E-Commerce Public Dataset by Olist sur Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). La fiche décrit environ 100 000 commandes sur la période 2016–2018 et neuf fichiers CSV couvrant commandes, clients, articles, paiements, avis, produits, vendeurs, géolocalisation et traduction des catégories. Les données ont été anonymisées par leur fournisseur.

Le jeu source est publié sous licence **CC BY-NC-SA 4.0**. Les données brutes ne sont pas incluses dans ce dépôt : le script les télécharge localement dans `data/raw/`, dossier ignoré par Git. Toute redistribution ou utilisation commerciale des données et de leurs adaptations doit respecter les termes de cette licence. Attribution : Olist, *Brazilian E-Commerce Public Dataset by Olist*, [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), licence [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## Ce que le pipeline contrôle

- **Complétude** : valeurs manquantes par table et par colonne, en volume et en pourcentage.
- **Unicité** : unicité des clés primaires déclarées dans les tables de commandes, clients, articles, paiements, produits, vendeurs et traduction.
- **Intégrité référentielle** : liens entre commandes, clients, articles, produits, vendeurs, paiements et avis.
- **Validité** : domaine des statuts, ordre chronologique des dates, valeurs monétaires et coordonnées géographiques dans leurs plages attendues.
- **Suivi opérationnel** : retards par rapport à la date de livraison estimée, présentés comme signal métier plutôt que comme erreur technique.

Chaque règle conserve le nombre de lignes vérifiées, le nombre de lignes en échec, un taux d’échec, une catégorie et une priorité. Les commentaires d’avis sont suivis comme champs facultatifs ; les dates de livraison sont contrôlées seulement pour les commandes livrées. Le score présenté est la moyenne des scores par table ; chaque score de table vaut 100 moins la moyenne des taux d’échec des règles applicables à cette table. Les champs facultatifs sont exclus de ce score. Il s’agit d’un indicateur de pilotage, pas d’une certification de conformité.

Sur l’exécution de référence, le pipeline a profilé **1 550 922 lignes dans neuf tables** et exécuté **78 règles**. Il a relevé 12 contrôles en échec : principalement des retards de livraison par rapport à la date estimée et des attributs produits incomplets. Les commentaires laissés sur les avis sont affichés dans le profil de complétude, mais ne sont pas classés comme anomalies puisque ces champs sont facultatifs. Ces chiffres peuvent varier si la source Kaggle est mise à jour.

## Lancer le projet

Pré-requis : Python 3.10 ou supérieur.

```bash
git clone https://github.com/fatma-analytics/olist-data-quality-monitoring.git
cd olist-data-quality-monitoring
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\\Scripts\\activate
pip install -r requirements.txt
python scripts/download_data.py
python src/quality_monitor.py
streamlit run dashboard/app.py
```

Le pipeline crée les fichiers suivants dans `outputs/` :

- `run_summary.csv` : indicateurs de la dernière exécution ;
- `table_quality.csv` : volume, score et contrôles par table ;
- `column_quality.csv` : taux de valeurs manquantes et cardinalité par colonne ;
- `quality_issues.csv` : règles en échec et niveau de priorité ;
- `check_results.csv` : résultats complets des règles, y compris les contrôles conformes.

Les sorties sont générées localement et ne sont pas publiées dans le dépôt. Le tableau de bord s’ouvre après exécution du pipeline.

## Rapport Power BI

Depuis Power BI Desktop, importez les cinq CSV du dossier `outputs/`. Reliez `table_quality` à `check_results` et `quality_issues` via `table_name`. Pour la complétude par colonne, utilisez `column_quality` comme table de profil et le détail de `check_results` ; les règles de plusieurs colonnes restent des contrôles de table et ne doivent pas être dupliquées dans le profil colonne. Le fichier [`powerbi/Measures.dax`](powerbi/Measures.dax) fournit les mesures de base.

Mise en page proposée :

1. bandeau KPI avec score global, anomalies ouvertes, règles en échec et lignes profilées ;
2. histogramme horizontal du score par table, avec seuils de lecture à 95 % et 99 % ;
3. matrice des anomalies par catégorie et priorité ;
4. détail filtrable des règles en échec ;
5. tableau des colonnes les plus incomplètes.

La couche SQL DuckDB de [`sql/quality_and_mart.sql`](sql/quality_and_mart.sql) crée une vue de faits à la granularité commande. Les montants des articles et les paiements sont agrégés avant les jointures afin d’éviter la multiplication artificielle des lignes.

## Structure

```text
├── dashboard/app.py              # Tableau de bord interactif Streamlit
├── data/raw/                     # Sources locales, exclues du dépôt
├── powerbi/Measures.dax          # Mesures DAX de départ
├── scripts/download_data.py      # Téléchargement des fichiers Kaggle
├── sql/quality_and_mart.sql      # Modèle analytique et contrôles DuckDB
├── src/quality_monitor.py        # Profilage, règles et exports BI
├── tests/                        # Tests unitaires des contrôles
└── outputs/                      # Résultats locaux, générés par le pipeline
```

## Tests

```bash
pytest -q
```

## Licences

Le code source de ce projet est publié sous licence MIT. Le jeu Olist reste soumis à sa licence propre CC BY-NC-SA 4.0 ; les conditions du jeu prévalent pour les données et leurs adaptations.
