from google.cloud import bigquery
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    r"fathur-project-488913-6fdfbec23bce.json"
)

client = bigquery.Client(
    credentials=credentials,
    project="fathur-project-488913"
)

# Ganti seluruh bagian query kamu dengan ini
combined_query = """
BEGIN
  DECLARE v_keyset BYTES;

  -- 1. Ambil keyset langsung di dalam BigQuery
  SET v_keyset = (
    SELECT keyset
    FROM `fathur-project-488913.secret.permanent_keyset`
    WHERE key_name = 'my_deterministic_key'
    LIMIT 1
  );

  -- 2. Jalankan enkripsi menggunakan EXECUTE IMMEDIATE
  EXECUTE IMMEDIATE '''
    CREATE OR REPLACE TABLE `fathur-project-488913.l2_fathur.dummy_users_100k_encrypted_py_delegation_decript` AS
    SELECT
      d.user_id,
      DETERMINISTIC_DECRYPT_STRING(
        KEYS.KEYSET_CHAIN(
          "gcp-kms://projects/fathur-project-488913/locations/asia-southeast2/keyRings/keyring-pii/cryptoKeys/key-pii",
          @keyset_val
        ),
        d.encrypted_phone,
        ""
      ) AS decrypted_phone,
      d.created_at
    FROM `fathur-project-488913.l2_fathur.dummy_users_100k_encrypted_py_delegation` d
  ''' USING v_keyset AS keyset_val;
END;
"""

# Jalankan tanpa JobConfig parameter karena keyset sudah diurus di dalam SQL
job = client.query(combined_query)
job.result()

print("decryption via Scripting completed successfully.")