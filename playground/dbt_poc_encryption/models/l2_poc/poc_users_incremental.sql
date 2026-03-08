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