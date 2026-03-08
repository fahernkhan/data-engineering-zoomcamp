
  
    

    create or replace table `fathur-project-488913`.`l2_poc`.`poc_users_incremental_2`
      
    
    

    
    OPTIONS()
    as (
      

SELECT
    user_id,
    username,
    encrypted_email,
    encrypted_phone,
    created_at
FROM `fathur-project-488913`.`l2_poc`.`poc_stg_users_encrypted`
    );
  