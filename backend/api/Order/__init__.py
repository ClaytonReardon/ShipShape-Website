import os
import logging
import pyodbc
import azure.functions as func
import json

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

def get_stock(item_query):
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT stock FROM Inventory WHERE item_name = ?", item_query,)
            row = cursor.fetchone()
            if row:
                return func.HttpResponse(str(row[0]))
            else:
                return func.HttpResponse(f"Item {item_query} not found", status_code=404)

def order_item(item_query, quantity):
    try:
        quantity = int(quantity)
    except ValueError:
        return func.HttpResponse("Invalid quantity provided", status_code=400)
    
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE Inventory SET stock = stock - ? WHERE item_name = ?", (quantity, item_query))
            cursor.commit()
            if cursor.rowcount > 0:
                return func.HttpResponse(f"Order for {item_query} placed successfully")
            else:
                return func.HttpResponse(f"Failed to place order for {item_query}")