-- models/marts/poc_users_incremental.sql


with src as (
    select user_id, username, encrypted_email, encrypted_phone, created_at
    from `fathur-project-488913`.`l2_poc`.`poc_stg_users_encrypted`
    
      where created_at > (select max(created_at) from `fathur-project-488913`.`l2_poc`.`poc_users_incremental`)
    
)

select * from src