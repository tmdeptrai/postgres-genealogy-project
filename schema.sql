DROP TABLE IF EXISTS "department" CASCADE;
DROP TABLE IF EXISTS "town" CASCADE;
DROP TABLE IF EXISTS "person" CASCADE;
DROP TABLE IF EXISTS "act" CASCADE;

CREATE TABLE IF NOT EXISTS "department" (
  "code" varchar(2) PRIMARY KEY
  CONSTRAINT "chk_valid_dept" CHECK ("code" IN ('44', '49', '79', '85'))
);

CREATE TABLE IF NOT EXISTS "town" (
  "id" SERIAL PRIMARY KEY,
  "name" varchar(255) NOT NULL,
  "dept_code" varchar(2) NOT NULL,
  FOREIGN KEY ("dept_code") REFERENCES "department"("code")
);

CREATE TABLE IF NOT EXISTS "person" (
  "id" SERIAL PRIMARY KEY,
  "last_name" varchar(255) NOT NULL,
  "first_name" varchar(255) NOT NULL,
  "father_id" integer REFERENCES "person"("id"),
  "mother_id" integer REFERENCES "person"("id")
);

CREATE TABLE IF NOT EXISTS "act" (
  "id" integer PRIMARY KEY,
  "act_type" varchar(50) NOT NULL,
  "a_id" integer NOT NULL REFERENCES "person"("id"),
  "b_id" integer NOT NULL REFERENCES "person"("id"),
  "town_id" integer NOT NULL REFERENCES "town"("id"),
  "act_date" date NOT NULL,
  "view_num" integer,
  CONSTRAINT "chk_act_type" CHECK ("act_type" IN (
        'Certificat de mariage',
        'Contrat de mariage',
        'Divorce',
        'Mariage',
        'Promesse de mariage - fiançailles',
        'Publication de mariage',
        'Rectification de mariage'
    ))
);  

-- QUERY FOR QUESTIONS --
-- 1. La quantité de communes par département
-- Number of towns per department
SELECT dept_code, COUNT(*) AS total_town 
FROM town
GROUP BY dept_code;

-- 2. La quantité de actes à LUÇON
-- Number of acts that belong to the town LUÇON
SELECT COUNT(*)
FROM act
JOIN town ON act.town_id = town.id
WHERE town.name ~* '^LUÇON$';

-- 3. La quantité de “contrats de mariage” avant 1855
-- Number of marriage contracts before 1855
SELECT COUNT(*)
FROM act
WHERE act.act_type = "Contrat de mariage"
AND act.date < '1855-01-01';

-- 4. La commune avec la plus quantité de “publications de mariage”
-- Town with the most "publications de mariage"
SELECT town.name, COUNT(*) AS total_publications
FROM act
JOIN town ON act.town_id = town.id
WHERE act.act_type = "Publication de mariage"
GROUP BY town.name
ORDER BY total_publications DESC
LIMIT 1;

-- 5. La date du premier acte et le dernier acte
-- Date of the first act and last act
SELECT MIN(date) as first_act, MAX(date) as last_act
FROM act;