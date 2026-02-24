## 1. Normalization:

### a) Champs initials

1. Identifiant d’acte
2. Type d’acte
3. Nom personne A
4. Prénom personne A
5. Prénom père personne A
6. Nom mère personne A
7. Prénom mère personne A
8. Nom personne B
9. Prénom personne B
10. Prénom père personne B
11. Nom mère personne B
12. Prénom mère personne B
13. Commune
14. Département
15. Date
16. Num Vue

### b) Normalisation

- 1NF:
  - Tous les valeurs sont déjà atomiques
  - Chaque enregistrement est identifié par un identifiant d'acte unique

  => 1NF

- 2NF:
  - **Problème** : Des répétitions pour les parents, les communes et les départements
  - **Solution** : Séparer les entités pour que chaque attribut non-clé dépend de la totalité de la clé primaire:

    ```
    Identifiant d’acte → (Type d’acte, Date, Num Vue, Commune, Personne A, Personne B)

    Identifiant de personne → (Nom, Prénom, Père_ID, Mère_ID)

    Commune → Département
    ```

  => 2NF

- 3NF:
  - **Problème** :
    - le **département** dépendait de la commune, qui elle-même dépendait de l'acte (Dépendance Transitive).
    - les noms des parents dépendaient de la personne A/B
  - **Solution** :
    - Extraire **Departement** dans une table propre
    - Créer les clés étrangères (pere_id, mere_id) pointant vers la table **Personne**

    => 3NF

### c) Dépendances fonctionnels finals:

```
Identifiant d’acte → {Type d’acte, Date, Num Vue, Commune, Personne A, Personne B}

Personne_ID → {Nom, Prénom, Père_ID, Mère_ID}

Commune_ID → {Nom Commune, Code Département}

Père_ID → {Prénom Père}

Mère_ID → {Nom Mère, Prénom Mère}
```

## Schéma

![alt text](db_schema.png)

## Création des tables en Postgresql

```sql
CREATE TABLE IF NOT EXISTS "departement" (
	"code" varchar(2) PRIMARY KEY,
);

CREATE TABLE IF NOT EXISTS "commune" (
	"id" integer PRIMARY KEY,
	"nom" varchar(255) NOT NULL,
	"dept_code" varchar(255) NOT NULL,
);

CREATE TABLE IF NOT EXISTS "personne" (
	"id" integer PRIMARY KEY,
	"nom" varchar(255) NOT NULL,
	"prenom" varchar(255) NOT NULL,
	"pere_id" integer,
	"mere_id" integer,
);

CREATE TABLE IF NOT EXISTS "acte" (
	"id" integer PRIMARY KEY,
	"type_acte" varchar(50) NOT NULL,
	"personne_a_id" integer NOT NULL,
	"personne_b_id" integer NOT NULL,
	"commune_id" integer NOT NULL,
	"date_acte" date NOT NULL,
	"num_vue" integer NOT NULL,

    CONSTRAINT "chk_type_acte" CHECK ("type_acte" IN (
        'Certificat de mariage', 'Contrat de mariage', 'Divorce',
        'Mariage', 'Promesse de mariage - fiançailles',
        'Publication de mariage', 'Rectification de mariage'
    ))
);


ALTER TABLE "commune" ADD CONSTRAINT "commune_fk2" FOREIGN KEY ("dept_code") REFERENCES "departement"("code");
ALTER TABLE "personne" ADD CONSTRAINT "personne_fk3" FOREIGN KEY ("pere_id") REFERENCES "personne"("id");

ALTER TABLE "personne" ADD CONSTRAINT "personne_fk4" FOREIGN KEY ("mere_id") REFERENCES "personne"("id");
ALTER TABLE "acte" ADD CONSTRAINT "acte_fk2" FOREIGN KEY ("personne_a_id") REFERENCES "personne"("id");

ALTER TABLE "acte" ADD CONSTRAINT "acte_fk3" FOREIGN KEY ("personne_b_id") REFERENCES "personne"("id");

ALTER TABLE "acte" ADD CONSTRAINT "acte_fk4" FOREIGN KEY ("commune_id") REFERENCES "commune"("id");
```
