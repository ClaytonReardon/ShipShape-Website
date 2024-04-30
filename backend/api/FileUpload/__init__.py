import os, uuid
import azure.functions as func
import logging
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions, UserDelegationKey
import datetime
import magic
from pathvalidate import sanitize_filename
import re
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Function to create SAS token 
def create_service_sas_blob(blob_client: BlobClient, blob_service_client: BlobServiceClient, blob_name: str):
    # Get user delegation key
    udk_start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=15)
    udk_expiry_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=1)
    user_delegation_key = blob_service_client.get_user_delegation_key(udk_start_time, udk_expiry_time)

    # Create SAS token that's valid for one day
    expiry_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)

    sas_token = generate_blob_sas(
        account_name=blob_client.account_name,
        container_name=blob_client.container_name,
        blob_name=blob_name,
        permission=BlobSasPermissions(read=True),
        expiry=udk_expiry_time,
        user_delegation_key=user_delegation_key,
    )

    return sas_token

def sanitize_and_format_filename(original_name):
    # Sanitize filename to remove invalid characters
    sanitized = sanitize_filename(original_name, platform="auto")
    # Regex to remove special characters
    sanitized = re.sub(r'[!@#$%^&*(){}\[\]:;"\'`\\|?/><,]+', '', sanitized)
    # Split the filename from its extension
    base, ext = os.path.splitext(sanitized)
    # Remove all dots from the base part
    base = base.replace('.', '')
    # Append a UUID to ensure uniqueness
    sanitized = f"{base}-{uuid.uuid4().hex[:6]}.{ext}"

    return sanitized

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("\nPython HTTP trigger function processed a request\n")

    try:
        logging.info("\nConnecting to Azure Blob Storage\n")
        
        # Connect to Blob Storage
        account_url = os.getenv('ACCOUNT_NAME')
        default_credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(account_url, credential=default_credential)
        container_name = os.getenv('CONT_NAME')

        # Get file from request
        logging.info("\nGetting file from POST request & renaming\n")
        file = req.files['file']
        original_name = file.filename

        # Check extension
        if not original_name.lower().endswith('.json'):
            return func.HttpResponse("Only .json files are accepted", status_code=400)

        # Mime type check
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(file.stream.read(2048)) # read first 2048 bytes to determine MIME 
        file.stream.seek(0) # Reset stream position after reading
        if detected_mime != 'application/json':
            return func.HttpResponse("File is not a valid JSON file", status_code=400)
        
        file_name = sanitize_and_format_filename(original_name)

        # Create blob client using local file name as blob name
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)

        # Upload created file
        logging.info("\nUploading file & creating SAS token\n")
        blob_client.upload_blob(file.stream, overwrite=True)

        # Print SAS Token
        sas_token = create_service_sas_blob(blob_client, blob_service_client, file_name)
        sas_url = f"{blob_client.url}?{sas_token}"

        # Send JSON to Logic App
        file.stream.seek(0) # Reset stream to read content
        json_data = file.stream.read().decode('utf-8') # Read and decode stream
        logic_app_url = os.getenv('LOGIC_APP_URL')
        response = requests.post(logic_app_url, headers={'Content-Type': 'application/json'}, data=json_data)
        if response.status_code != 202:
            logging.error("Error sending data to Logic App: " + response.text)
            return func.HttpResponse("Failed to send data to Logic App.", status_code=500)

        return func.HttpResponse(sas_url, status_code=200, headers={"Content-Type": "text/plain"})

    except Exception as ex:
        logging.exception('Exception occured: ' + str(ex))
        return func.HttpResponse("Failed to process the upload and generate SAS token.", status_code=500)
