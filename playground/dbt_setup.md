Aku akan buat **Flow Dokumentasi Lengkap (End-to-End)** supaya kamu bisa:

* setup **dbt dari 0**
* test **encryption pipeline**
* test **dbt incremental**
* test **decryption**
* validasi **di BigQuery console**
* jalankan semua **command dbt di CMD/PowerShell**

Dokumentasi ini bisa kamu jadikan **README project / portfolio Data Engineer**.

---

# 1. Arsitektur Pipeline

Pipeline yang kamu buat sebenarnya sudah **enterprise-style**.

```
RAW DATA
   │
   ▼
L1 (Encrypted Layer)
   │
   │  BigQuery SQL Encryption
   ▼
users_encrypted
   │
   ▼
DBT Transformation
   │
   ├── staging view
   ├── incremental table
   ▼
L2 Analytics Layer
   │
   ▼
Decryption Report
   │
   ├── BigQuery scripting
   └── Python / Macro
```

Dataset:

```
l1_poc
l2_poc
poc_secret
```

---

# 2. Setup DBT dari Awal

## 2.1 Buat virtual environment

CMD / PowerShell:

```bash
python -m venv .venv
```

activate:

```bash
.venv\Scripts\activate
```

---

## 2.2 Install dbt BigQuery

```bash
pip install dbt-bigquery
```

cek:

```bash
dbt --version
```

harus muncul:

```
dbt 1.11.x
adapter bigquery
```

---

# 3. Initialize Project DBT

buat project:

```bash
dbt init dbt_poc_encryption
```

masuk folder:

```bash
cd dbt_poc_encryption
```

struktur awal:

```
dbt_poc_encryption
│
├─ dbt_project.yml
├─ models
│   └─ example
└─ macros
```

hapus folder example:

```
models/example
```

---

# 4. Setup profiles.yml

lokasi biasanya:

```
C:\Users\Lenovo\.dbt\profiles.yml
```

isi:

```yaml
dbt_poc_encryption:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: fathur-project-488913
      dataset: l2_poc
      keyfile: C:/path/service-account.json
      location: asia-southeast2
      threads: 4
```

---

# 5. Test Koneksi DBT

CMD:

```bash
dbt debug
```

expected:

```
Connection test: OK
All checks passed
```

---

# 6. Struktur Model DBT

```
models
│
├── staging
│   └── poc_stg_users_encrypted.sql
│
├── incremental
│   └── poc_users_incremental.sql
```

---

# 7. Staging Model

```
models/staging/poc_stg_users_encrypted.sql
```

```sql
SELECT
    user_id,
    username,
    encrypted_email,
    encrypted_phone,
    normalized_email,
    normalized_phone,
    created_at
FROM `fathur-project-488913.l1_poc.users_encrypted`
```

---

# 8. Incremental Model

```
models/incremental/poc_users_incremental.sql
```

```sql
{{ config(
    materialized='incremental',
    unique_key='user_id'
) }}

SELECT
    user_id,
    username,
    encrypted_email,
    encrypted_phone,
    created_at
FROM {{ ref('poc_stg_users_encrypted') }}

{% if is_incremental() %}

WHERE created_at >
(
SELECT MAX(created_at)
FROM {{ this }}
)

{% endif %}
```

---

# 9. Jalankan DBT Model

di CMD / PowerShell:

### compile

```bash
dbt compile
```

---

### run semua model

```bash
dbt run
```

---

### run model tertentu

```bash
dbt run --select poc_users_incremental
```

---

### run staging saja

```bash
dbt run --select poc_stg_users_encrypted
```

---

### run test

```bash
dbt test
```

---

# 10. Validasi di BigQuery Console

## cek table incremental

```sql
SELECT *
FROM `fathur-project-488913.l2_poc.poc_users_incremental`
LIMIT 10
```

---

## cek total row

```sql
SELECT COUNT(*)
FROM `fathur-project-488913.l2_poc.poc_users_incremental`
```

---

## cek max created_at

```sql
SELECT MAX(created_at)
FROM `fathur-project-488913.l2_poc.poc_users_incremental`
```

---

# 11. Test Encryption Pipeline

jalankan SQL di BigQuery console.

## insert dummy users

```sql
CREATE OR REPLACE TABLE `fathur-project-488913.l1_poc.users_new_raw` AS
SELECT 10001 AS user_id, 'user10001' AS username, 'user10001@gmail.com' AS email, '081100010001' AS phone_number, CURRENT_TIMESTAMP() AS created_at
UNION ALL
SELECT 10002, 'user10002', 'user10002@yahoo.com', '081100010002', CURRENT_TIMESTAMP()
UNION ALL
SELECT 10003, 'user10003', 'user10003@example.co.id', '081100010003', CURRENT_TIMESTAMP();
```

---

## encrypt data

gunakan query yang kamu punya:

```sql
DECLARE v_keyset BYTES;
SET v_keyset = (
SELECT keyset
FROM `fathur-project-488913.poc_secret.permanent_keyset`
WHERE key_name='my_deterministic_key'
);

EXECUTE IMMEDIATE """
INSERT INTO `fathur-project-488913.l1_poc.users_encrypted`
SELECT
user_id,
username,
LOWER(TRIM(email)),
REGEXP_REPLACE(phone_number,r'[^0-9]',''),
created_at,

DETERMINISTIC_ENCRYPT(
KEYS.KEYSET_CHAIN(
'gcp-kms://projects/fathur-project-488913/locations/asia-southeast2/keyRings/keyring-pii/cryptoKeys/key-pii',
@keyset
),
LOWER(TRIM(email)),
''
),

DETERMINISTIC_ENCRYPT(
KEYS.KEYSET_CHAIN(
'gcp-kms://projects/fathur-project-488913/locations/asia-southeast2/keyRings/keyring-pii/cryptoKeys/key-pii',
@keyset
),
REGEXP_REPLACE(phone_number,r'[^0-9]',''),
''
)

FROM `fathur-project-488913.l1_poc.users_new_raw`
"""
USING v_keyset AS keyset;
```

---

# 12. Test Incremental DBT

jalankan:

```bash
dbt run --select poc_users_incremental
```

cek di BigQuery:

```sql
SELECT *
FROM `fathur-project-488913.l2_poc.poc_users_incremental`
WHERE user_id IN (10001,10002,10003)
```

---

# 13. Test Decryption

di BigQuery console:

```sql
DECLARE v_keyset BYTES;

SET v_keyset =
(
SELECT keyset
FROM `fathur-project-488913.poc_secret.permanent_keyset`
WHERE key_name='my_deterministic_key'
);

CREATE OR REPLACE TABLE `fathur-project-488913.l2_poc.poc_users_decrypted_report`
AS
SELECT
user_id,
username,

DETERMINISTIC_DECRYPT_STRING(
KEYS.KEYSET_CHAIN(
'gcp-kms://projects/fathur-project-488913/locations/asia-southeast2/keyRings/keyring-pii/cryptoKeys/key-pii',
v_keyset
),
encrypted_email,
''
) AS email_plain,

created_at

FROM `fathur-project-488913.l2_poc.poc_users_incremental`;
```

---

## validasi hasil

```sql
SELECT *
FROM `fathur-project-488913.l2_poc.poc_users_decrypted_report`
```

email harus muncul kembali.

---

# 14. Test Join Encrypted

tanpa decrypt:

```sql
SELECT u.username,o.amount
FROM `fathur-project-488913.l1_poc.users_encrypted` u
JOIN `fathur-project-488913.l1_poc.orders_encrypted` o
ON u.encrypted_email=o.encrypted_email
```

ini membuktikan **deterministic encryption**.

---

# 15. Lesson Learned (Paling Penting)

### 1. Encryption harus dilakukan di layer awal

```
RAW → ENCRYPT → TRANSFORM
```

bukan:

```
RAW → TRANSFORM → ENCRYPT
```

---

### 2. Deterministic encryption memungkinkan join

tanpa decrypt.

```
users_encrypted
orders_encrypted
JOIN encrypted_email
```

---

### 3. dbt tidak ideal untuk encryption

dbt cocok untuk:

```
transform
aggregation
modeling
```

bukan untuk:

```
key management
encryption
decryption
```

---

### 4. BigQuery KEYSET_CHAIN punya constraint

```
argument must be literal or parameter
```

makanya decrypt di dbt model sering error.

---

### 5. incremental logic harus hati-hati

kasus kamu:

```
created_at > max(created_at)
```

kalau timestamp lebih kecil → data tidak masuk incremental.

---

### 6. Encrypted data tidak bisa diubah

harus:

```
decrypt → transform → encrypt ulang
```

---

### 7. Production pipeline biasanya

```
Airflow / Python
      │
      ├── Encryption
      ├── Key rotation
      ▼
BigQuery
      │
      ▼
dbt models
      │
      ▼
Analytics layer
```

---

# 16. Flow Final Project

```
1 create raw users
2 encrypt → users_encrypted
3 dbt run
4 incremental table
5 decrypt report
6 validate
```

---

# 17. Command Cheat Sheet (CMD)

```bash
# activate env
.venv\Scripts\activate

# test connection
dbt debug

# compile models
dbt compile

# run all models
dbt run

# run specific model
dbt run --select poc_users_incremental

# run tests
dbt test

# run macro
dbt run-operation create_decrypted_report
```

---

Jika kamu mau, aku juga bisa bantu kamu membuat **versi final arsitektur ini seperti production system (level senior data engineer)** yang biasanya dipakai di:

```
Google
Stripe
Gojek
Tokopedia
```

karena PoC kamu ini sebenarnya **sudah hampir sampai level production encryption pipeline**.