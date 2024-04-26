import os
import logging
import pyodbc
import azure.functions as func
import bcrypt
import random

connection_string = os.getenv('SQL_CONN_STR')

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP Trigger function processed a request.')
    try:
        # Parse body for username and password
        req_body = req.get_json()
        username = req_body.get('username')
        password = req_body.get('password')
        user_id = generate_user_id()

        if not username or not password:
            return func.HttpResponse(
                "Please pass both username and password in the request body",
                status_code=400
            )
        
        create_account(user_id, username,password)

        return func.HttpResponse(f"User {username} created successfully!", status_code = 201)
    except ValueError:
        return func.HttpResponse("Bad request", status_code=400)
    
def generate_user_id():
    return random.randint(100000, 999999)
    
    
def hash_password(password):
    salt = bcrypt.gensalt(12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

def create_account(user_id, username, password):
    hashed_password = hash_password(password)
    query = "INSERT INTO Users (user_id, username, password) VALUES (?, ?, ?);"

    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id, username, hashed_password))
            conn.commit()