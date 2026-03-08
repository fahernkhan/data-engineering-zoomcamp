
  
    

    create or replace table `fathur-project-488913`.`l2_poc`.`poc_users_decrypted_report`
      
    
    

    
    OPTIONS()
    as (
      -- models/marts/poc_users_decrypted_report.sql


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
from `fathur-project-488913`.`l2_poc`.`poc_users_incremental` u
    );
  