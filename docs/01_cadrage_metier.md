# Cadrage métier

> Ce document formalise le besoin **avant** l'analyse. Dans un projet réel, c'est le livrable
> validé avec le commanditaire : il évite de produire des chiffres qui ne répondent à aucune question.

## 1. Contexte

Une compagnie opératrice de taxis jaunes à New York (entreprise fictive, données réelles) exploite
une flotte de Yellow Cabs. En 2019, le secteur est sous pression :

- **concurrence des VTC** (Uber, Lyft), qui captent une part croissante des trajets ;
- **congestion** chronique de Manhattan, qui allonge les courses sans augmenter proportionnellement leur prix ;
- **surtaxe de congestion** de 2,50 $ par course dans le sud de Manhattan, entrée en vigueur le 2 février 2019.
  Janvier 2019 constitue donc la **période de référence** avant son application.

La direction des opérations dispose des données de courses publiées par la NYC Taxi & Limousine
Commission (TLC), mais les exploite peu : fichiers bruts volumineux, erreurs de saisie, aucun indicateur partagé.

## 2. Problématique

> **Où et quand positionner les chauffeurs pour maximiser le revenu généré par heure de conduite ?**

Sous-questions :

| # | Question métier | Décision éclairée |
|---|---|---|
| Q1 | Quand la demande est-elle la plus forte (heure, jour) ? | Planning des équipes, nombre de véhicules en service |
| Q2 | À quelle heure une minute de course rapporte-t-elle le plus ? | Incitations horaires, créneaux à privilégier |
| Q3 | Quels types de course (aéroport, intra-Manhattan...) portent le CA et la productivité ? | Stratégie de positionnement |
| Q4 | Quelles zones concentrent le chiffre d'affaires ? | Zones d'attente prioritaires |
| Q5 | Courses courtes ou longues : lesquelles sont les plus rentables ? | Consignes aux chauffeurs |
| Q6 | Quel est le comportement de paiement et de pourboire ? | Politique de paiement (terminaux carte) |
| Q7 | Comment l'activité varie-t-elle selon le jour et les jours fériés ? | Prévision d'activité |
| Q8 | Peut-on faire confiance aux données ? | Crédibilité des décisions |

## 3. Parties prenantes

| Acteur | Attente |
|---|---|
| Directeur des opérations (commanditaire) | Vision synthétique, recommandations actionnables |
| Responsable planning | Demande par heure et jour |
| Chauffeurs (via les managers) | Où et quand travailler pour mieux gagner |
| Équipe data | Pipeline fiable, traçable et reproductible |

## 4. Indicateurs clés (KPI)

| KPI | Définition | Pourquoi |
|---|---|---|
| Nombre de courses | Courses valides sur la période | Volume d'activité |
| Chiffre d'affaires (CA) | Somme de `total_amount` (tarif, suppléments, taxes, péages, pourboires carte) | Valeur générée |
| Panier moyen | CA / courses | Valeur d'une course |
| **Revenu par minute** | CA / minutes passées avec un client | **KPI central** : productivité du temps de conduite |
| Vitesse moyenne | Distance / durée | Indicateur de congestion |
| Part du CA | CA du segment / CA total | Poids d'un segment |
| Taux de pourboire (carte) | Pourboires / tarif, paiements carte | Satisfaction client, revenu chauffeur |
| Taux de données exploitables | Courses analysées / courses brutes | Confiance dans les chiffres |

**Pourquoi le revenu par minute plutôt que le panier moyen ?** Une course aéroport rapporte 51 $
mais immobilise le chauffeur 32 minutes ; une course intra-Manhattan rapporte 12 $ en 11 minutes.
Pour un chauffeur, la ressource rare est le **temps** : c'est donc le revenu par unité de temps qui
permet de comparer des courses de nature différente.

## 5. Périmètre

- **Inclus** : Yellow Taxis, janvier 2019, 7,67 millions de courses brutes, 265 zones TLC.
- **Exclus** : taxis verts, VTC, autres mois (voir Limites dans le README).

## 6. Livrables

1. Pipeline de données fiable (Bronze, Silver, Gold) avec contrôles qualité tracés.
2. Analyses SQL répondant aux questions Q1 à Q8.
3. Dashboard Power BI de 5 pages destiné à la direction des opérations.
4. Synthèse des résultats et recommandations (README et `docs/04_synthese_resultats.md`).
