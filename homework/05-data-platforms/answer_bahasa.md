Tentu, berikut adalah panduan yang lebih jelas dan komprehensif untuk mengerjakan Module 5 Homework. Selain langkah-langkah teknis, saya sertakan **lesson learn** (apa yang dipelajari) dan **flow penting** yang perlu dipahami agar Anda tidak hanya bisa menjawab soal, tetapi juga menguasai konsep data platform dengan Bruin.

---

# 🚀 Panduan Lengkap + Lesson Learn Module 5 Homework (Bruin Data Platform)

## 🎯 Tujuan Akhir
Membangun pipeline data end-to-end untuk dataset NYC Taxi menggunakan Bruin, serta memahami konsep-konsep kunci seperti **struktur proyek, materialisasi inkremental, variabel, quality checks, lineage, dan deployment**.

---

## 📚 Apa yang Akan Dipelajari (Lesson Learn)

| Konsep | Implementasi di Homework | Mengapa Penting? |
|--------|---------------------------|-------------------|
| **Struktur Proyek Data Platform** | Membuat proyek Bruin, memahami peran `.bruin.yml`, `pipeline.yml`, dan folder `assets/`. | Setiap data platform punya standar struktur. Bruin mengajarkan separation of concern: konfigurasi vs kode vs pipeline definition. |
| **Koneksi Database & Environment** | Mengonfigurasi koneksi DuckDB di `.bruin.yml`. | Data pipeline harus bisa terhubung ke berbagai environment (dev, prod). Bruin menggunakan file YAML untuk mengelola koneksi dan env. |
| **Materialisasi Inkremental Berbasis Waktu** | Menggunakan `strategy: time_interval` pada aset SQL untuk memproses data per bulan. | Ini adalah pola umum dalam ELT untuk efisiensi: hanya memproses data baru atau interval tertentu, bukan seluruh tabel. |
| **Variabel Pipeline & Override Runtime** | Mendefinisikan variabel `taxi_types` di `pipeline.yml` dan menimpanya dengan `--var`. | Pipeline harus fleksibel. Variabel memungkinkan parameterisasi tanpa mengubah kode. |
| **Menjalankan Subset Pipeline (DAG-aware)** | Menggunakan `--select asset+` untuk menjalankan aset tertentu beserta semua dependensinya. | Dalam DAG, seringkali kita hanya ingin menjalankan satu bagian dan semua yang bergantung padanya (misal setelah memperbaiki kode di hulu). |
| **Data Quality sebagai Kode** | Menambahkan `not_null` check pada kolom `pickup_datetime` di metadata aset. | Menjamin kepercayaan data. Quality check dijalankan otomatis setiap pipeline berjalan. |
| **Lineage & Observability** | Melihat dependency graph dengan `bruin lineage`. | Memahami alur data dari sumber ke laporan membantu debugging dan dokumentasi. |
| **First-time Run & Full Refresh** | Menggunakan `--full-refresh` untuk menjalankan pipeline di database baru. | Di awal pengembangan atau setelah perubahan struktur, kita perlu membuat ulang tabel dari awal. |

---

## 🔄 Flow Penting yang Harus Dipahami

### 1. **Alur Pengembangan Pipeline**
```
Inisialisasi Proyek → Konfigurasi Koneksi → Buat Aset (ingestion, staging, mart) → Tambah Quality Check → Validasi → Jalankan Pipeline (full-refresh pertama) → Iterasi (ubah aset, jalankan dengan --select) → Lihat Lineage → Deploy ke Cloud/CI
```

### 2. **Alur Data dalam Pipeline**
```
Sumber Eksternal (API/File) → Aset Ingestion (ingestr) → Tabel Raw di DuckDB → Aset Staging (SQL, materialized sebagai tabel) → Tabel Staging → Aset Mart/Report (SQL, view/table) → Siap Dianalisis
```

### 3. **Alur Eksekusi dengan Dependency**
```
Ketika menjalankan `bruin run --select staging.stg_trips+`, Bruin akan:
- Menjalankan `ingestion.trips_raw` (jika belum pernah atau ada perubahan)
- Menjalankan `staging.stg_trips` (aset yang dipilih)
- Menjalankan semua aset yang bergantung pada `staging.stg_trips` (misal `reports.daily_trips`)
```

---

## 🛠️ Langkah-Langkah Detail (Dari Nol Sampai Submit)

### Langkah 0: Instalasi & Inisialisasi
```bash
# Install Bruin
curl -LsSf https://getbruin.com/install/cli | sh

# Verifikasi
bruin --version

# Inisialisasi proyek dari template Zoomcamp
bruin init zoomcamp my-taxi-pipeline
cd my-taxi-pipeline
```

### Langkah 1: Konfigurasi Environment & Koneksi (Q1)
- Buka file `.bruin.yml`
- Isi dengan koneksi DuckDB:
  ```yaml
  default_environment: default
  environments:
    default:
      connections:
        duckdb:
          - name: "duckdb"
            path: "nyc_taxi.duckdb"
  ```
**Lesson Learn**: `.bruin.yml` memisahkan konfigurasi sensitif (seperti credentials) dari kode pipeline. Ini penting untuk keamanan dan portabilitas.

### Langkah 2: Definisikan Pipeline & Variabel (Q3)
- Buka `pipeline.yml`
- Pastikan ada variabel `taxi_types`:
  ```yaml
  name: nyc_taxi_pipeline
  default_connections:
    duckdb: duckdb
  variables:
    taxi_types:
      type: array
      items:
        type: string
      default: ["yellow", "green"]
  ```
**Lesson Learn**: Variabel memungkinkan pipeline yang sama digunakan untuk skenario berbeda (misal hanya proses taksi kuning) tanpa mengubah kode aset.

### Langkah 3: Buat Aset Ingestion
- Ikuti petunjuk di template, atau buat file `assets/ingestion/trips_raw.asset.yml`:
  ```yaml
  name: ingestion.trips_raw
  type: ingestr
  parameters:
    source:
      type: http
      url: "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"
    destination:
      type: duckdb
      table: raw_trips
  columns:
    - name: tpep_pickup_datetime
      type: timestamp
    - name: tpep_dropoff_datetime
      type: timestamp
  ```
**Catatan**: Ganti URL dengan file yang sesuai. Template Zoomcamp biasanya sudah menyediakan contoh.

### Langkah 4: Buat Aset Staging dengan Materialisasi Inkremental (Q2)
- Buat file `assets/staging/stg_trips.sql`:
  ```sql
  /* @bruin
  name: staging.stg_trips
  type: duckdb.sql
  materialization:
    type: table
    strategy: time_interval
    incremental_key: pickup_datetime
    time_granularity: month
  depends:
    - ingestion.trips_raw
  columns:
    - name: pickup_datetime
      checks:
        - name: not_null   # <-- Q5
  */

  SELECT
    VendorID,
    tpep_pickup_datetime AS pickup_datetime,
    tpep_dropoff_datetime AS dropoff_datetime,
    passenger_count,
    trip_distance,
    fare_amount
  FROM ingestion.trips_raw
  WHERE pickup_datetime BETWEEN '{{ start_date }}' AND '{{ end_date }}';
  ```
**Lesson Learn**: `time_interval` adalah strategi yang tepat untuk data waktu. Bruin secara otomatis akan menghapus data di interval yang diproses dan mengisinya kembali, sehingga idempotent.

### Langkah 5: Tambahkan Quality Check (Q5)
- Pada file yang sama di atas, di bagian `columns`, kita sudah menambahkan `not_null` untuk `pickup_datetime`.
- **Penting**: Quality check di Bruin bersifat *blocking*: jika gagal, pipeline akan berhenti. Ini menjamin data yang masuk ke tahap selanjutnya bersih.

### Langkah 6: Validasi Pipeline
```bash
bruin validate
```
Perbaiki jika ada error.

### Langkah 7: Jalankan Pipeline Pertama Kali (Q7)
```bash
bruin run --full-refresh
```
Flag `--full-refresh` akan membuat ulang semua tabel dari awal. Cocok untuk first run di database kosong.

### Langkah 8: Uji Override Variabel (Q3)
```bash
bruin run --var 'taxi_types=["yellow"]'
```
Perhatikan bagaimana pipeline hanya memproses data taksi kuning (jika variabel digunakan di aset). Ini membuktikan fleksibilitas variabel.

### Langkah 9: Jalankan Aset Tertentu + Downstream (Q4)
Misal Anda mengubah aset `ingestion.trips_raw`:
```bash
bruin run --select ingestion.trips_raw+
```
Simbol `+` berarti "aset ini dan semua dependensinya". Ini sangat efisien saat development.

### Langkah 10: Lihat Lineage (Q6)
```bash
bruin lineage
```
Perintah ini akan menampilkan grafik dependensi (dapat diekspor ke format gambar). Anda bisa melihat bahwa `staging.stg_trips` bergantung pada `ingestion.trips_raw`, dan seterusnya.

### Langkah 11: (Opsional) Deploy ke Bruin Cloud
- Daftar di [Bruin Cloud](https://getbruin.com)
- Hubungkan repository GitHub
- Tambahkan koneksi ke warehouse (misal BigQuery)
- Deploy pipeline dan pantau eksekusi.

---

## 📝 Ringkasan Jawaban Homework

| Soal | Jawaban | Berdasarkan Praktik di Atas |
|------|---------|------------------------------|
| 1 | `.bruin.yml` and `pipeline.yml` (assets can be anywhere) | Struktur proyek setelah `bruin init` |
| 2 | `time_interval` | Strategi di aset staging |
| 3 | `bruin run --var 'taxi_types=["yellow"]'` | Cara override variabel array |
| 4 | `bruin run --select ingestion.trips+` | Menjalankan aset + downstream |
| 5 | `name: not_null` | Quality check di metadata kolom |
| 6 | `bruin lineage` | Perintah untuk melihat lineage |
| 7 | `--full-refresh` | Flag untuk first-time run |

---

## 💡 Tips Penting

1. **Gunakan VS Code Extension Bruin** untuk syntax highlighting dan auto-completion saat menulis metadata.
2. **Selalu jalankan `bruin validate` sebelum `bruin run`** untuk menangkap kesalahan lebih awal.
3. **Pahami perbedaan `--full-refresh` dan `--var`**: `--full-refresh` untuk reset struktur, `--var` untuk parameter runtime.
4. **Quality checks bukan hanya `not_null`**, pelajari juga `unique`, `accepted_values`, `row_count`, dll. untuk pipeline yang lebih robust.
5. **Lineage sangat membantu dokumentasi**: Anda bisa membagikan gambar lineage ke tim untuk menjelaskan alur data.

---

## 🎓 Kesimpulan Akhir

Dengan mengerjakan homework ini, Anda telah mempraktikkan siklus hidup pengembangan data platform modern menggunakan Bruin. Anda tidak hanya belajar alat, tetapi juga **pola pikir data engineering**: idempotency, incremental processing, data quality, dan observability. Semua ini adalah fondasi untuk membangun pipeline data yang andal di industri.

Selamat, Anda telah menyelesaikan Module 5! 🎉

Tentu, berdasarkan dokumentasi resmi Bruin, berikut adalah panduan langkah demi langkah dalam format `.md` yang jelas dan terstruktur untuk mengerjakan **Jadi Kesimpulannya Untuk Module 5 Homework** dari awal hingga akhir.

Panduan ini akan memandu Anda membangun pipeline data NYC Taxi sambil secara langsung mempraktikkan konsep-konsep yang ditanyakan dalam soal.

---

# 🚀 Panduan Lengkap Mengerjakan Module 5 Homework: Data Platforms dengan Bruin

Panduan ini akan membantu Anda menjawab semua pertanyaan homework dengan mempraktikkan langsung setiap konsep menggunakan Bruin dan dataset NYC Taxi.

## ✅ Prasyarat & Setup Awal

1.  **Instal Bruin CLI**:
    Buka terminal dan jalankan perintah berikut:
    ```bash
    curl -LsSf https://getbruin.com/install/cli | sh
    ```
    *Sumber: [Dokumentasi Instalasi Bruin]*.

2.  **Inisialisasi Proyek dari Template Zoomcamp**:
    Perintah ini akan membuat struktur proyek dasar yang kita butuhkan.
    ```bash
    bruin init zoomcamp my-taxi-pipeline
    cd my-taxi-pipeline
    ```
    *Sumber: [Panduan Template Zoomcamp Bruin]*.

3.  **Konfigurasi Koneksi Database**:
    Buka file `.bruin.yml`. Kita akan menggunakan DuckDB untuk kesederhanaan. Isi dengan konfigurasi berikut:
    ```yaml
    default_environment: default
    environments:
      default:
        connections:
          duckdb:
            - name: "duckdb"
              path: "my_duckdb.db"
    ```
    *(Pertanyaan 1: Di sinilah file konfigurasi `.bruin.yml` berada)*.

## 📝 Panduan Menjawab Pertanyaan Homework (Satu per Satu)

### Pertanyaan 1: Struktur Pipeline Bruin
> **Praktik Langsung:**
> Jalankan `tree` atau `ls -la` di direktori `my-taxi-pipeline`. Anda akan melihat:
> *   `.bruin.yml` (file konfigurasi environment & koneksi)
> *   `pipeline.yml` (definisi pipeline utama)
> *   Folder `assets/` (tempat semua file SQL/Python/ingestr berada)
>
> **Kesimpulan untuk Jawaban:** Struktur yang benar adalah `.bruin.yml` dan `pipeline.yml`, sementara aset bisa diletakkan di mana saja (biasanya di folder `assets/`).

### Pertanyaan 2: Strategi Materialization untuk Data Bulanan
> **Praktik Langsung:**
> Buat file aset staging di `assets/staging/stg_trips.sql`. Isi dengan metadata Bruin untuk materialisasi inkremental berdasarkan waktu.
>
> ```sql
> /* @bruin
> name: staging.stg_trips
> type: duckdb.sql
> materialization:
>   type: table
>   strategy: time_interval
>   incremental_key: pickup_datetime
>   time_granularity: month
> depends:
>   - ingestion.trips_raw
> */
>
> SELECT
>   VendorID,
>   tpep_pickup_datetime as pickup_datetime,
>   -- ... kolom lainnya
> FROM ingestion.trips_raw
> WHERE pickup_datetime BETWEEN '{{ start_date }}' AND '{{ end_date }}';
> ```
> **Kesimpulan untuk Jawaban:** Strategi `time_interval` adalah yang paling tepat untuk memproses data per periode waktu (bulanan) dengan menghapus dan memasukkan ulang data untuk interval tersebut.

### Pertanyaan 3: Menimpa (Override) Variabel Pipeline
> **Praktik Langsung:**
> 1.  Buka `pipeline.yml` dan pastikan ada definisi variabel array:
>     ```yaml
>     name: nyc_taxi_pipeline
>     variables:
>       taxi_types:
>         type: array
>         items:
>           type: string
>         default: ["yellow", "green"]
>     ```
> 2.  Jalankan pipeline dengan perintah berikut untuk hanya memproses taksi kuning:
>     ```bash
>     bruin run --var 'taxi_types=["yellow"]'
>     ```
>     *Sumber: [Dokumentasi Perintah `bruin run`]*.
> **Kesimpulan untuk Jawaban:** Cara yang benar adalah menggunakan `--var` dengan nilai array dalam format JSON.

### Pertanyaan 4: Menjalankan Aset dan Semua Dependensi Hilirnya
> **Praktik Langsung:**
> Anggap Anda baru saja mengubah aset `ingestion.trips_raw` (misalnya, file `assets/ingestion/trips_raw.asset.yml`). Untuk menjalankan aset ini dan semua aset yang bergantung padanya (seperti `staging.stg_trips`), gunakan:
> ```bash
> bruin run --select ingestion.trips_raw+
> ```
> Simbol `+` memberitahu Bruin untuk menyertakan semua dependen (downstream).
> *Sumber: [Dokumentasi Seleksi Aset Bruin]*.
> **Kesimpulan untuk Jawaban:** Perintah yang tepat adalah `bruin run --select ingestion.trips+`.

### Pertanyaan 5: Menambahkan Pemeriksaan Kualitas (Quality Check) `not_null`
> **Praktik Langsung:**
> Tambahkan blok `columns` ke dalam metadata file aset Anda (misalnya, di `staging.stg_trips.sql`) untuk memastikan kolom `pickup_datetime` tidak pernah `NULL`.
>
> ```sql
> /* @bruin
> name: staging.stg_trips
> ... (materialization, dll) ...
> columns:
>   - name: pickup_datetime
>     checks:
>       - name: not_null
> depends:
>   - ingestion.trips_raw
> */
> ```
> *Sumber: [Dokumentasi Pemeriksaan Data Bruin]*.
> **Kesimpulan untuk Jawaban:** Pemeriksaan yang benar adalah `name: not_null`.

### Pertanyaan 6: Melihat Lineage dan Dependensi
> **Praktik Langsung:**
> Untuk melihat grafik dependensi antar aset yang telah Anda buat, jalankan perintah:
> ```bash
> bruin lineage
> ```
> Perintah ini akan menampilkan visualisasi alur data dari hulu ke hilir.
> *Sumber: [Dokumentasi Perintah `bruin lineage`]*.
> **Kesimpulan untuk Jawaban:** Perintah yang digunakan adalah `bruin lineage`.

### Pertanyaan 7: Menjalankan Pipeline untuk Pertama Kali
> **Praktik Langsung:**
> Karena ini adalah pertama kalinya Anda menjalankan pipeline di database DuckDB yang baru (file `my_duckdb.db`), Anda perlu membuat semua tabel dari awal. Gunakan flag `--full-refresh`:
> ```bash
> bruin run --full-refresh
> ```
> Flag ini akan memaksa Bruin untuk menghapus dan membuat ulang tabel yang diperlukan.
> *Sumber: [Dokumentasi Perintah `bruin run`]*.
> **Kesimpulan untuk Jawaban:** Flag yang tepat adalah `--full-refresh`.

## 📌 Ringkasan Alur Eksekusi Homework

1.  **Setup**: Instal Bruin, inisialisasi proyek, konfigurasi `.bruin.yml`.
2.  **Buat Aset**: Ikuti petunjuk di `assets/ingestion`, `assets/staging`, dan `assets/reports` pada template Zoomcamp.
    *   Implementasikan `time_interval` di aset SQL (Q2).
    *   Tambahkan `not_null` check di metadata aset (Q5).
3.  **Jalankan Pipeline**:
    *   **Pertama kali**: `bruin run --full-refresh` (Q7).
    *   **Override variabel**: `bruin run --var 'taxi_types=["yellow"]'` (Q3).
    *   **Jalankan aset + downstream**: `bruin run --select ingestion.trips_raw+` (Q4).
4.  **Eksplorasi & Verifikasi**:
    *   Lihat lineage: `bruin lineage` (Q6).
    *   Struktur proyek: `ls` (Q1).

Dengan mengikuti langkah-langkah di atas, Anda tidak hanya akan mendapatkan jawaban yang benar untuk setiap pertanyaan, tetapi juga membangun pemahaman praktis tentang cara kerja Bruin sebagai sebuah data platform. Selamat mencoba!