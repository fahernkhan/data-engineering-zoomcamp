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