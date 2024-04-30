import unittest
from unittest.mock import patch, MagicMock
from azure.functions import HttpRequest
from api.Order.__init__ import main, get_stock, order_item
import json
import os

class TestInventoryFunction(unittest.TestCase):
    @patch('api.Order.__init__.pyodbc.connect')
    @patch('api.Order.__init__.time.sleep', return_value=None)
    @patch.dict(os.environ, {'SQL_CONN_STR': 'fake_connection_string'})
    def test_get_stock_success(self, mock_sleep, mock_connect):
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [10]

        request = HttpRequest(method="GET", url="/", params={"item": "test_item"}, body='')
        response = main(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_body().decode(), '10')
    
    @patch('api.Order.__init__.pyodbc.connect')
    @patch.dict(os.environ, {'SQL_CONN_STR': 'fake_connection_string'})
    def test_post_order_success(self, mock_connect):
        # Mock set up
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1

        body = json.dumps({"item": "test_item", "quantity": "5"})
        request = HttpRequest(method="POST", url="/", body=body.encode())
        response = main(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("placed successfully", response.get_body().decode())
    
    @patch('api.Order.__init__.pyodbc.connect')
    @patch.dict(os.environ, {'SQL_CONN_STR': 'fake_connection_string'})
    def test_post_invalid_json(self, mock_connect):
        body = "{bad json}"
        request = HttpRequest(method="POST", url="/", body=body.encode())
        response = main(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid JSON", response.get_body().decode())

if __name__ == '__main__':
    unittest.main()