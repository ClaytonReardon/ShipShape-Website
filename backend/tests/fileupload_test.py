import unittest
from unittest.mock import patch, MagicMock
import azure.functions as func
from api.FileUpload.__init__ import main, create_service_sas_blob,sanitize_and_format_filename
import re
import os
import json

def setUpModule():  # Load settings once for all tests in this module
    os.environ['LOGIC_APP_URL'] = os.getenv('LOGIC_APP_URL')

class TestFileUploadFunction(unittest.TestCase):
    @patch('api.FileUpload.__init__.requests.post')
    @patch('api.FileUpload.__init__.magic')
    @patch('api.FileUpload.__init__.generate_blob_sas', return_value="sas_token_string")
    @patch('api.FileUpload.__init__.BlobServiceClient')
    @patch('api.FileUpload.__init__.DefaultAzureCredential')
    def test_file_upload_success(self, mock_default_credential, mock_blob_service_client, mock_generate_blob_sas, mock_magic, mock_requests_post):
        # Setup the mock for requests.post
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.text = 'Success'
        mock_requests_post.return_value = mock_response

        # Mock blob client to return a realistic URL
        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://example.blob.core.windows.net/container"
        mock_blob_container_client = MagicMock()
        mock_blob_container_client.get_blob_client.return_value = mock_blob_client
        mock_blob_service_client.return_value = mock_blob_container_client

        # Setup for other mocks
        mock_magic.Magic.return_value = MagicMock(mime=True, from_buffer=MagicMock(return_value='application/json'))

        # Create a mock request object
        mock_request = MagicMock()
        mock_request.files = {'file': MagicMock()}
        mock_file = mock_request.files['file']
        mock_file.filename = 'test.json'
        mock_file.stream.read.return_value = b'{"key": "value"}'
        mock_file.stream.seek.return_value = None

        # Execute the function
        response = main(mock_request)

        # Assertions
        expected_status = 200
        expected_url_start = "https://"
        actual_status = response.status_code
        actual_body = response.get_body().decode()
        self.assertEqual(expected_status, actual_status, f"Expected status code {expected_status}, but got {actual_status}")
        self.assertIn(expected_url_start, actual_body, f"Expected response body URL to start with '{expected_url_start}', but got '{actual_body}'")
    
    @patch('api.FileUpload.__init__.DefaultAzureCredential')
    @patch('api.FileUpload.__init__.BlobServiceClient')
    @patch('api.FileUpload.__init__.magic')
    def test_file_upload_invalid_extension(self, mock_magic, mock_blob_service_client, mock_default_credential):
        mock_request = MagicMock()
        mock_request.files = {'file': MagicMock()}
        mock_file = mock_request.files['file']
        mock_file.filename = 'test.txt' # Invalid extension

        # Mimic function behavior
        response = main(mock_request)

        # Assertions
        expected_status = 400
        expected_message = "Only .json files are accepted"
        actual_status = response.status_code
        actual_message = response.get_body().decode()
        self.assertEqual(actual_status, expected_status, f"Expected response code: {expected_status}, but got {actual_status}")
        self.assertIn(expected_message, actual_message, f"Expected error message to contain '{expected_message}', but got '{actual_message}'")

    def test_sanitize_and_format_filename_with_special_chars(self):
        original_name = "!@#$%^&*()]}[{;'....//..././test..json"
        sanitized_name = sanitize_and_format_filename(original_name)
        expected_base = "test-"
        self.assertIn(expected_base, sanitized_name, f"The base '{expected_base}' was not found in '{sanitized_name}'")
        self.assertTrue(sanitized_name.endswith(".json"), f"Filename '{sanitized_name}' does not end with '.json'")
        # Ensure no invalid characters remain
        invalid_chars = re.findall(r'[!@#$%^&*(){}\[\]:;"\'`\\|?/><,]+', sanitized_name)
        self.assertEqual(len(invalid_chars), 0, f"Invalid characters were found in '{sanitized_name}'")
        self.assertRegex(sanitized_name, r'^test-[0-9a-f]{6}\..json$', "The filename does not match the expected pattern 'test-[UUID].json'")

    
    # Run the tests
    if __name__ == '__main__':
        unittest.main()