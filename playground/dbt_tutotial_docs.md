Bagus — kamu sudah jalanin `dbt debug` & `dbt run` dan hasilnya PASS. Sekarang aku susun **skenario dbt lengkap (dari 0 → run → test)** yang sesuai nama datasetmu (`l1_poc`, `l2_poc`, `l3_poc`) + perbaikan deprecation (`+` prefix) + test cases untuk behavior encryption (join success/failure, keyset rotation, reprocess, incremental). Semua step dan file siap copy-paste ke project `dbt_poc_encryption` yang ada di `playground`.

Aku sertakan juga catatan penting (IAM & KMS permissions) dan referensi dokumentasi.

---

# Ringkasan langkah cepat

1. Pastikan service account JSON ada (`fathur-project-488913-6fdfbec23bce.json`) dan punya izin BigQuery + KMS decrypt.
2. Update `profiles.yml` → gunakan `project=fathur-project-488913` dan default `dataset` = `l2_poc` (dbt output).
3. Update `dbt_project.yml` → tambahkan `+` prefix untuk materialized config supaya tidak muncul deprecation warning.
4. Tambahkan models: `stg_users_encrypted.sql`, `poc_users_incremental.sql`, `poc_users_decrypted_report.sql`.
5. Tambahkan `schema.yml` untuk tests (count, unique, not_null, custom SQL tests).
6. Jalankan `dbt run` → `dbt test`.
7. Jalankan test scenarios manual (SQL) untuk key rotation, new keyset (ciphertext change), reprocessing, join failure.

Saya jelaskan tiap file & command di bawah.

---

# 0) Prasyarat IAM (penting)

Service account yang dipakai di `keyfile` harus punya:

* BigQuery permissions: `roles/bigquery.dataEditor` (atau minimal create/read/write tabel yang diperlukan).
* Cloud KMS permission untuk unwrap keyset: `roles/cloudkms.cryptoKeyDecrypter` pada CryptoKey (atau lebih aman: grant hanya pada principal yang butuh decrypt).
  Tanpa permission KMS, decryption (DETERMINISTIC_DECRYPT_STRING / keyset unwrap) akan error. (Docs AEAD/KEYSET_CHAIN). ([Google Cloud Documentation][1])

---

# 1) `profiles.yml` (letak: `dbt_poc_encryption/profiles.yml`)

Sesuaikan `keyfile` path ke location Windows-mu:

```yaml
poc_encryption:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: fathur-project-488913
      dataset: l2_poc            # dbt default target dataset (l2)
      keyfile: C:\Users\Lenovo\Documents\de-learn\data-engineering-zoomcamp\playground\fathur-project-488913-6fdfbec23bce.json
      threads: 4
      location: asia-southeast2
      priority: interactive
```

> catatan: dbt mencari `profiles.yml` di current working dir dulu (kamu menjalankan di folder project), jadi letakkan di `dbt_poc_encryption/` atau `~/.dbt/`. ([dbt Developer Hub][2])

---

# 2) `dbt_project.yml` (perbaikan + prefix)

Gunakan `+` prefix di config untuk menghindari deprecation warning:

```yaml
name: "dbt_poc_encryption"
version: "1.0"
config-version: 2

profile: "poc_encryption"

model-paths: ["models"]

models:
  dbt_poc_encryption:
    +staging:
      +materialized: view
    +marts:
      +materialized: incremental
```

Penjelasan: `+staging` adalah config path dan `+materialized` memastikan tidak muncul MissingPlusPrefixDeprecation. ([dbt Developer Hub][3])

---

# 3) Struktur models (letakkan di `dbt_poc_encryption/models/`)

## a) `models/staging/poc_stg_users_encrypted.sql`

Simple source view ke L1 (data terenkripsi sudah ada di `l1_poc`):

```sql
-- models/staging/poc_stg_users_encrypted.sql
{{ config(materialized='view') }}

select
  user_id,
  username,
  encrypted_email,
  encrypted_phone,
  created_at
from `fathur-project-488913.l1_poc.users_encrypted`
```

## b) `models/marts/poc_users_incremental.sql`

Incremental model (materialized incremental) — `unique_key = user_id` (stabil, karena encrypted value bisa berubah saat re-encrypt).

```sql
-- models/marts/poc_users_incremental.sql
{{ config(
    materialized='incremental',
    unique_key='user_id'
) }}

with src as (
    select user_id, username, encrypted_email, encrypted_phone, created_at
    from {{ ref('poc_stg_users_encrypted') }}
    {% if is_incremental() %}
      where created_at > (select max(created_at) from {{ this }})
    {% endif %}
)

select * from src
```

Catatan: jangan gunakan encrypted column sebagai `unique_key` kalau nanti kamu ingin rewrap/regen keyset — gunakan `user_id`.

## c) `models/marts/poc_users_decrypted_report.sql` (optional; only authorized)

Model ini **akan melakukan decrypt** — hanya boleh dijalankan oleh principal yang punya KMS decrypt.

```sql
-- models/marts/poc_users_decrypted_report.sql
{{ config(materialized='table') }}

select
  u.user_id,
  u.username,
  DETERMINISTIC_DECRYPT_STRING(
    KEYS.KEYSET_CHAIN(
      'gcp-kms://projects/fathur-project-488913/locations/asia-southeast2/keyRings/keyring-pii/cryptoKeys/key-pii',
      (
        select keyset
        from `fathur-project-488913.poc_secret.permanent_keyset`
        where key_name='my_deterministic_key'
      )
    ),
    u.encrypted_email,
    ''
  ) as email_plain,
  u.created_at
from {{ ref('poc_users_incremental') }} u
```

> Hati-hati: menjalankan model ini memanggil Cloud KMS saat build. Pastikan role & audit. ([Google Cloud Documentation][4])

---

# 4) `schema.yml` (tests)

Letakkan `models/marts/schema.yml` untuk menambahkan dbt tests:

```yaml
version: 2
models:
  - name: poc_users_incremental
    description: "Incremental users table (encrypted input)."
    columns:
      - name: user_id
        tests:
          - not_null
          - unique
      - name: encrypted_email
        tests:
          - not_null

  - name: poc_users_decrypted_report
    columns:
      - name: email_plain
        tests:
          - not_null
```

Jalankan `dbt test` setelah `dbt run`.

---

# 5) Tambahan macro (opsional) — helper decrypt only-if-authorized

Buat folder `macros/` dan file `macros/decrypt_helpers.sql`:

```sql
-- macros/decrypt_helpers.sql
{% macro decrypt_email(ciphercol) %}
  DETERMINISTIC_DECRYPT_STRING(
    KEYS.KEYSET_CHAIN(
      'gcp-kms://projects/fathur-project-488913/locations/asia-southeast2/keyRings/keyring-pii/cryptoKeys/key-pii',
      (
        select keyset
        from `fathur-project-488913.poc_secret.permanent_keyset`
        where key_name='my_deterministic_key'
      )
    ),
    {{ ciphercol }},
    ''
  )
{% endmacro %}
```

Lalu di report model bisa pake `{{ decrypt_email('u.encrypted_email') }}`.

---

# 6) Commands run (urut-urutan)

Di folder project (`dbt_poc_encryption`):

```bash
# debug connection
dbt debug

# compile & run all models
dbt run

# run only staging
dbt run --select poc_stg_users_encrypted

# run a single model (incremental)
dbt run --select poc_users_incremental

# run tests defined in schema.yml
dbt test

# run only data tests (if any)
dbt test --select state:modified
```

---

# 7) Skenario testing (operasional) — langkah & SQL verification

### Test A — Baseline: join success (single keyset)

1. Pastikan `poc_secret.permanent_keyset` ada.
2. Pastikan `l1_poc.users_encrypted` & `l1_poc.orders_encrypted` dibuat menggunakan **sama** wrapped keyset.
3. Jalankan `dbt run` → `dbt test`.
4. Verifier SQL (manual):

```sql
SELECT COUNT(*) as cnt
FROM `fathur-project-488913.l1_poc.users_encrypted` u
JOIN `fathur-project-488913.l1_poc.orders_encrypted` o
  ON u.encrypted_email = o.encrypted_email;
```

Expect: `cnt > 0`. (join berjalan karena deterministic encryption). ([Google Cloud Documentation][1])

---

### Test B — Rewrap/new keyset → ciphertext berubah → join gagal

1. Buat new wrapped keyset (NEW_WRAPPED_KEYSET) dan simpan sebagai another keyset.
2. Re-encrypt orders table with new keyset (simulate orders_encrypted_v2).
3. Run verifier:

```sql
SELECT COUNT(*) as cnt
FROM `fathur-project-488913.l1_poc.users_encrypted` u
JOIN `fathur-project-488913.l1_poc.orders_encrypted_v2` o
  ON u.encrypted_email = o.encrypted_email;
```

Expect: `cnt = 0` (ciphertext different) — ini menunjukkan need to reprocess historical or use deterministic strategy consistent. (Test case dbt: ensure `unique_key` is stable and reprocessing triggered). ([Google Cloud Documentation][1])

---

### Test C — KMS key rotation but same DEK (unwrap behavior)

* If kamu **rotate KMS key version** but use **same wrapped keyset** (or rewrap to same DEK) ciphertext stays same. (Implement in staging before prod). Verify same as Test A.

Reference: AEAD doc explains keyset must contain the key used, etc. ([Google Cloud Documentation][1])

---

### Test D — Reprocessing historical L1 then dbt incremental

Skenario: kamu perbaiki cleansing rule (LOWER/TRIM) dan perlu re-encrypt. Steps:

1. Run re-encryption SQL to create new `l1_poc.users_encrypted_reprocessed`.
2. Swap or point staging to new table (or drop & replace `l1_poc.users_encrypted`).
3. Run `dbt run --select poc_users_incremental --full-refresh` (full rebuild) OR design a controlled reprocess: if you use `user_id` as unique_key, incremental will detect changed `created_at` based filter maybe — lebih aman `--full-refresh` untuk sinkronisasi historis.
   Command:

```bash
dbt run --select poc_users_incremental --full-refresh
```

---

### Test E — Automated dbt tests you can add for scenarios

Tambahkan SQL tests (`tests/`) or use `dbt-utils` macros for row_count comparators. Example custom data test to assert join rows > 0:

`tests/assert_users_orders_join.sql`:

```sql
select count(*) as cnt
from `fathur-project-488913.l1_poc.users_encrypted` u
join `fathur-project-488913.l1_poc.orders_encrypted` o on u.encrypted_email=o.encrypted_email
having cnt > 0
```

dbt supports `data_test` pattern; you can implement as `.sql` inside `tests/`. If test returns 0 rows => fail.

---

# 8) Troubleshooting & common gotchas

* **Deprecation warning**: jika masih muncul, pastikan semua configs di `dbt_project.yml` memakai `+` for config entries (not file names). ([dbt Developer Hub][5])
* **KMS permission error**: `PERMISSION_DENIED` when decrypting — ensure SA has `cloudkms.cryptoKeyDecrypter`.
* **Join returns 0**: likely different keyset / different normalization (e.g. one side not LOWER/TRIM). Re-check normalization before encryption (cleaning must run at L1).
* **dbt incremental uniqueness broken**: if `unique_key` uses encrypted field and ciphertext changed after re-encrypt → duplicates / missed updates. Use stable PK (user_id).
* **profiles.yml location**: if dbt can't find it, place in `~/.dbt/profiles.yml` or current working directory. ([dbt Developer Hub][2])

---

# 9) Quick checklist to run now (copy & run)

1. Update `profiles.yml` and `dbt_project.yml` as di atas.
2. Letakkan models & macros files sesuai path.
3. `cd dbt_poc_encryption`
4. `dbt debug` → pastikan OK.
5. `dbt run` → should create `l2_poc` models.
6. `dbt test` → run tests.
7. Run manual SQL tests (join verification etc.) in BigQuery console.

---

# Referensi singkat

* BigQuery AEAD / DETERMINISTIC functions (docs). ([Google Cloud Documentation][1])
* dbt `+` prefix deprecation & usage. ([dbt Developer Hub][3])
* dbt BigQuery setup & profiles examples. ([dbt Developer Hub][6])

---

Kalau mau, aku bisa:

* 1. Generate file-by-file (isi lengkap) dalam pesan berikut supaya kamu tinggal `git clone` / copy-paste; **atau**
* 2. Jalankan checklist verifikasi untuk satu skenario (mis. buat `users_10` → encrypt → run dbt → test join) dan aku kasih commands/expected output baris-per-baris.

Pilih mana — mau aku kirim semua file lengkap sekarang?

[1]: https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/aead_encryption_functions?utm_source=chatgpt.com "AEAD encryption functions | BigQuery"
[2]: https://docs.getdbt.com/docs/core/connect-data-platform/connection-profiles?utm_source=chatgpt.com "Connection profiles | dbt Developer Hub"
[3]: https://docs.getdbt.com/reference/resource-configs/plus-prefix?utm_source=chatgpt.com "Using the + prefix | dbt Developer Hub"
[4]: https://docs.cloud.google.com/bigquery/docs/column-key-encrypt?hl=id&utm_source=chatgpt.com "Enkripsi level kolom dengan Cloud KMS | BigQuery"
[5]: https://docs.getdbt.com/reference/deprecations?utm_source=chatgpt.com "Deprecations | dbt Developer Hub"
[6]: https://docs.getdbt.com/docs/core/connect-data-platform/bigquery-setup?utm_source=chatgpt.com "BigQuery setup | dbt Developer Hub"
