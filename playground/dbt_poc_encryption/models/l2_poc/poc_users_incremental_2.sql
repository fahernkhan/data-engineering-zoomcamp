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