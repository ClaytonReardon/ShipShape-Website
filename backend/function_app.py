import os, uuid
import azure.functions as func
import logging
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
import datetime
import magic
from pathvalidate import sanitize_filename

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Function to create SAS token 
def create_service_sas_blob(blob_client: BlobClient, account_key: str, blob_name: str):
    # Create SAS token that's valid for one day
    expiry_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)

    sas_token = generate_blob_sas(
        account_name=blob_client.account_name,
        container_name=blob_client.container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
    )

    return sas_token

def sanitize_and_format_filename(original_name):
    # Sanitize filename to remove invalid characters
    sanitized = sanitize_filename(original_name, platform="auto")

    # Split the filename from its extension
    parts = sanitized.rsplit('.', 1)
    if len(parts) == 2:
        base, ext = parts
        base = base.replace('.', '')  # Remove all dots from the base part
    else:
        # If there's no extension dot, remove all dots
        print("Filename did not have extension")
    
    # Append a UUID to ensure uniqueness
    sanitized = f"{base}-{uuid.uuid4().hex[:6]}.{ext}"

    return sanitized

@app.route(route="fileupload", methods=['POST'])
def fileupload(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("\nPython HTTP trigger function processed a request\n")

    try:
        print("\nConnecting to Azure Blob Storage\n")
        
        # Connect to Blob Storage
        account_url = os.getenv('ACCOUNT_NAME')
        default_credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(account_url, credential=default_credential)
        container_name = os.getenv('CONTAINER_NAME')

        # Get file from request
        print("\nGetting file from POST request & renaming\n")
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
        print("\nUploading file & creating SAS token\n")
        blob_client.upload_blob(file.stream, overwrite=True)

        # Print SAS Token
        sas_token = create_service_sas_blob(blob_client, os.getenv('STORAGE_KEY'), file_name)
        sas_url = f"{blob_client.url}?{sas_token}"
        print("\nSAS Token:\n", sas_url)

        return func.HttpResponse(sas_url, status_code=200)

    except Exception as ex:
        print('Exception:')
        return func.HttpResponse("Failed to process the upload and generate SAS token.", status_code=500)
