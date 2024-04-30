import os
import logging
import pyodbc
import azure.functions as func
import json
import time

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

connection_string = os.getenv('SQL_CONN_STR')

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    method = req.method
    item_query = req.params.get('item')

    if method == "GET":
        return get_stock(item_query)
    elif method == "POST":
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse("Invalid JSON", status_code=400)
        
        item_query = body.get('item')
        quantity = body.get('quantity')

        if not item_query or quantity is None:
            return func.HttpResponse(
                "Please specify 'item' and 'quantity' in the JSON body of the request",
                status_code=400
            )
        
        return order_item(item_query, quantity)

    else:
        return func.HttpResponse(
            "Only GET and POST methods are supported.",
            status_code=405
        )                                  

def connect_with_retry(connection_string, max_attempts=10):
    for attempt in range(max_attempts):
        try:
            print(f"Attempting to connect to database, attempt {attempt + 1}")
            return pyodbc.connect(connection_string, timeout=10)
        except pyodbc.OperationalError as e:
            if 'HYT00' in str(e) and attempt < max_attempts - 1:
                sleep_time = 2 ** attempt # Exponentially increase try time
                print(f"Connection attempt {attempt+1} failed. Retrying after {sleep_time} seconds...")
                time.sleep(sleep_time)
        else:
            raise
    raise Exception("Failed to connect to the database after several attempts")

def get_stock(item_query):
    try:
        conn = connect_with_retry(connection_string)
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT stock FROM Inventory WHERE item_name = ?", item_query,)
                row = cursor.fetchone()
                if row:
                    return func.HttpResponse(str(row[0]))
                else:
                    return func.HttpResponse(f"Item {item_query} not found", status_code=404)
    except Exception as e:
        logging.error(f"Error in getting stock: {e}")
        return func.HttpResponse("Error processing your request", status_code=500)

def order_item(item_query, quantity):
    try:
        quantity = int(quantity)
        conn = connect_with_retry(connection_string)
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE Inventory SET stock = stock - ? WHERE item_name = ?", (quantity, item_query))
                cursor.commit()
                if cursor.rowcount > 0:
                    return func.HttpResponse(f"Order for {item_query} placed successfully")
                else:
                    return func.HttpResponse(f"Failed to place order for {item_query}")
    except ValueError:
        return func.HttpResponse("Invalid quantity provided", status_code=400)
    except Exception as e:
        logging.error(f"Error in ordering item: {e}")
        return func.HttpResponse("Error processing your request", status_code=500)