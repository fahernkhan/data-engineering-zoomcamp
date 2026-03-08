{% macro create_decrypted_report() %}

{% set sql %}
DECLARE v_keyset BYTES;

SET v_keyset = (
  SELECT keyset
  FROM `fathur-project-488913.poc_secret.permanent_keyset`
  WHERE key_name='my_deterministic_key'
  LIMIT 1
);

EXECUTE IMMEDIATE """
CREATE OR REPLACE TABLE `fathur-project-488913.l2_poc.poc_users_decrypted_report` AS
SELECT
  user_id,
  username,

  DETERMINISTIC_DECRYPT_STRING(
    KEYS.KEYSET_CHAIN(
      'gcp-kms://projects/fathur-project-488913/locations/asia-southeast2/keyRings/keyring-pii/cryptoKeys/key-pii',
      @keyset_param
    ),
    encrypted_email,
    ''
  ) AS email_plain,

  created_at

FROM `fathur-project-488913.l2_poc.poc_users_incremental`
"""
USING v_keyset AS keyset_param;

{% endset %}

{{ run_query(sql) }}

{% endmacro %}