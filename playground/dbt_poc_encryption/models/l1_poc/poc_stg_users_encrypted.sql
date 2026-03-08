-- models/staging/poc_stg_users_encrypted.sql
{{ config(materialized='view') }}

select
  user_id,
  username,
  encrypted_email,
  encrypted_phone,
  created_at
from `fathur-project-488913.l1_poc.users_encrypted`