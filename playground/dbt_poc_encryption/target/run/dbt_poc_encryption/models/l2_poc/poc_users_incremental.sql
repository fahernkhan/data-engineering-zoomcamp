-- back compat for old kwarg name
  
  
        
            
	    
	    
            
        
    

    

    merge into `fathur-project-488913`.`l2_poc`.`poc_users_incremental` as DBT_INTERNAL_DEST
        using (-- models/marts/poc_users_incremental.sql


with src as (
    select user_id, username, encrypted_email, encrypted_phone, created_at
    from `fathur-project-488913`.`l2_poc`.`poc_stg_users_encrypted`
    
      where created_at > (select max(created_at) from `fathur-project-488913`.`l2_poc`.`poc_users_incremental`)
    
)

select * from src
        ) as DBT_INTERNAL_SOURCE
        on ((DBT_INTERNAL_SOURCE.user_id = DBT_INTERNAL_DEST.user_id))

    
    when matched then update set
        `user_id` = DBT_INTERNAL_SOURCE.`user_id`,`username` = DBT_INTERNAL_SOURCE.`username`,`encrypted_email` = DBT_INTERNAL_SOURCE.`encrypted_email`,`encrypted_phone` = DBT_INTERNAL_SOURCE.`encrypted_phone`,`created_at` = DBT_INTERNAL_SOURCE.`created_at`
    

    when not matched then insert
        (`user_id`, `username`, `encrypted_email`, `encrypted_phone`, `created_at`)
    values
        (`user_id`, `username`, `encrypted_email`, `encrypted_phone`, `created_at`)


    