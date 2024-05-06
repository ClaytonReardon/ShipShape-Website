# Overview
In this section of my Azure Administration project I will be building the website for my fictional company, ShipShape. This section is the interface that space ship pilots will interact with to resupply and repair their ships. This will require them to upload their ship's status report as well as place orders for the supplies they need. I will build a Static Web App hosted in Azure. It will use 2 Azure Functions, one to facilitate uploading files to blob storage, and then returning an SAS URL, and another to query and update an SQL database. The file upload function will also link with a Logic App that will use ARM templates hosted in a Github repo to deploy network infrastructure and VMs based on the contents of the uploaded file. Once the VMs are deployed they will use the VM Custom Script Extension to execute a specified task upon boot up. The SQL Function App will also link to a Logic App to send order confirmation emails. Both Function and Logic Apps will use managed identities to follow the principal of least privilege. The whole frontend and backend of the site will be integrated with a Github workflow to provide a CI/CD pipeline. This means I will be able to edit the files locally, push them to Github, and the changes made to the static site and functions will be automatically deployed to Azure. This is part of my ongoing project for the [AZ-104 Azure Administration certification](https://learn.microsoft.com/en-us/credentials/certifications/azure-administrator/?practice-assessment-type=certification) to gain hands on experience with the objectives of that exam. This section of the project will focus on the "Manage Azure identities and governance", "Implement and manage storage", "Deploy and manage Azure compute resources", "Implement and manage virtual networking" objectives of the certification.
## Building Static Site
#### Homepage
The first thing I need to do is to build a static site that I can upload as a Static Web App to Azure. Now, keep in mind I am not a web developer and I don't pretend to be. The main purpose of this project is not web dev, but to learn about Azure. I apologize in advance for my messy HTML and CSS. I'll use Javascript to interact with the Azure functions, which will act as an API. I grab a free html template from [this site](https://www.free-css.com/free-css-templates) and make some modifications. I change the background image to match my theme, and I change the default font to [Jersey 10](https://fonts.google.com/specimen/Jersey+10?query=jersey+10). The template I chose has a carousel CSS function which i modify the only alternate the text below the site title. The home page I end up with looks like this:

![](2024-05-04_15-44_2.png)

The html for the main part of the page looks like this:
```html
    <!-- slider section -->
<section class="slider_section position-relative">
  <div class="container-fluid">
    <div id="carouselExampleIndicators" class="carousel slide" data-ride="carousel">
      <!-- Carousel inner content - where items will be cycled -->
      <div class="carousel-inner">
        <!-- Static content -->
        <div class="row justify-content-center align-items-center">
          <div class="col-md-8 text-center">
            <div class="detail-box">
              <h2>
                welcome to
              </h2>
              <h1>
                ShipShape
              </h1>
            </div>
          </div>
        </div>
        <!-- Cycling content - Only this part will cycle -->
        <div class="carousel-item active">
          <div class="row justify-content-center">
            <div class="col-md-8 text-center">
              <div class="detail-box">
                <p>We keep you supplied to get back in the skies</p>
              </div>
            </div>
          </div>
        </div>
        <div class="carousel-item">
          <div class="row justify-content-center">
            <div class="col-md-8 text-center">
              <div class="detail-box">
                <p>Laser crystals, rocket fuel, butyl/ketyl ethylene, droid parts, and more</p>
              </div>
            </div>
          </div>
        </div>
        <div class="carousel-item">
          <div class="row justify-content-center">
            <div class="col-md-8 text-center">
              <div class="detail-box">
                <p>Get your ship the care it needs to handle the rigors of space travel</p>
              </div>
            </div>
          </div>
        </div>
        <!-- Additional items to cycle would be added here -->
      </div>
      </a>  -->
    </div>
  </div>
</section>
<!-- end slider section -->
```
## File Upload Function
Now that I have a basic look and template for my site, I need to create an Azure Function that will receive a file from a POST request, upload it into blob storage, and then return an SAS URL for that file that expires after one day. The first thing  do is pop onto the Azure Portal and go to *Storage Accounts*, and create a new storage account. I create a new *ShipShapeRG* resource group and put in the region closest to me. For performance I leave it on *Standard* and for *Redundancy* I choose *Locally-redundant storage*, both of these to save costs. After this I have *Review + Create* and let it deploy
##### Best Practices Note:
Ideally, my storage account would be configured to exist inside a Vnet and only allow access from inside the Vnet and from my home IP address (for development purposes). However, to [use a secured storage account with a Function App](https://learn.microsoft.com/en-us/azure/azure-functions/configure-networking-how-to?tabs=portal) requires [integrating the function with a vnet using a private endpoint](https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-vnet) which is only possible with the Functions Premium plan. Which will drive my cost up quite a bit. If this website or project was going to be larger scale or handle more sensitive data, I would set this up.
![storage](2024-04-19_10-47.png)

Once the account is created I go into the *Access Control (IAM)* settings and click *Add Role Assignment*. I need to give myself *[Storage Blob Data Contributor](https://portal.azure.com/# "Storage Blob Data Contributor")* permissions to this resource, because even as the Global Admin, I won't be able to write files to the storage account without this permission. In the *Role* I search for and select *"Storage Blob Data Contributor*, and in the *Members* section I select myself, and then *Review+Assign*. With that done I go into *Containers* and select *+ Container*. I give it the name *"fileshare"* and click *Create*.

Now I hop into VS Code. Make sure you have the [Azure Functions](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions) extension installed. I hope into the Azure extension and click the lightning bolt icon in the workspace section, and select *"Create New Project*. I click browse and create 2 new folders: `backend/api` and select `api`. For language I choose *Python*, i select *Model V2*, for the template I choose *HTTP trigger*, I name the project "fileupload", and for authorization I select *ANONYMOUS*.

![func](2024-04-19_11-11.png)

Once this is done, some new files populate my `api` folder. The first thing I do is rearrange the file structure. I create a folder called `FileUpload` and move `function_app.py` into it and rename it `__init__.py`. I also create a file called `function.json` in this folder. Your folder structure should look like this:
```bash
ShipShape/backend/api
├── .venv
├── .funcignore
├── .gitignore
├── FileUpload
│   ├── function.json
│   └── __init__.py
├── host.json
├── local.settings.json
└── requirements.txt
```
My `function.json` file looks like this.
```json
{
    "scriptFile": "__init__.py",
    "bindings": [
      {
        "authLevel": "anonymous",
        "type": "httpTrigger",
        "direction": "in",
        "name": "req",
        "methods": ["post"]
      },
      {
        "type": "http",
        "direction": "out",
        "name": "$return"
      }
    ]
  }
```

I open up `__init__.py` which has the default starter code. To write this function, I consult [this page of documentation](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python?tabs=managed-identity%2Croles-azure-portal%2Csign-in-visual-studio-code&pivots=blob-storage-quickstart-scratch#authenticate-to-azure-and-authorize-access-to-blob-data) about the Azure Blob Storage library for python and how to interact with storage containers and blobs, as well as [this page of documentation](https://learn.microsoft.com/en-us/azure/storage/blobs/sas-service-create-python) about creating an SAS token with python.

The first thing I need to do is install 2 packages, `azure-storage-blob` and `azure-identity`. I add the 2 package names to `requirements.txt`. In VS code I open a new terminal in the `backend` directory and open the python virtual environment by running `source .venv/bin/activate`. After that I install the needed packages with `pip install -r requirements.txt`. 

I need my script to authenticate to Azure before I can interact with Blob Storage. There are 2 ways to do this, with a connection string, or the passwordless method using `DefaultAzureCredential()`. `DefaultAzureCredential()` supports multiple auth methods and will determine which method to use at runtime. This allows me to use different authentication methods in local vs production environments without having to change code. Locally, the Azure CLI can be used to authenticate, and then a managed identity can be used once it's been deployed to Azure. In the VS Code terminal I run `az login`, and proceed to login. I then add these 2 lines to my file:
```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
```
I then add 3 lines inside the `try` block, to authenticate to Azure and set the storage account and container name
```python
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("\nPython HTTP trigger function processed a request\n")

    try:
        logging.info("\nConnecting to Azure Blob Storage\n")
        # Connect to Blob Storage
        account_url = os.getenv('ACCOUNT_NAME')
        default_credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(account_url, credential=default_credential)
        container_name = os.getenv('CONT_NAME')
```
To add the environment variable `ACCOUNT_NAME` and `CONT_NAME` I go into `local.settings.json` and add this line to the `Values` section:
```json
"ACCOUNT_NAME": "https://<STORAGE_ACCOUNT_NAME>.blob.core.windows.net",
"CONT_NAME": "<CONTAINER NAME>"
```
##### Weird Bug
I experienced an extremely weird bug at this point that took me awhile to troubleshoot. I originally used the variable name `CONTAINER_NAME`, and when i did this, I started getting some extremely strange output when the running the function. It was generating all sorts of error messages and it was one of the most obscenely verbose and ugly output logs I've ever seen. The strangest part was the function still entirely worked. I even tested this later when the function was fully complete by setting the variable name back to `CONTAINER_NAME`. The function would upload the file to blob storage and generate the SAS URL perfectly, but I still had this bizarre output log. Turns out what fixed it was not using the name `CONTAINER_NAME` for the variable. My best guess for why this happened is that VS Code or Azure or something in the environment was already using that variable name and this caused a clash that resulted in this strange behavior. All this to say, do not use `CONTAINER_NAME` as the environment variable for your container name.

I then follow the docs example to test uploading a blob to azure and make sure my authentication works. Once that's successful I make some modifications.

I also edit the `app.route` line to accept HTTP POST requests.
```python
@app.route(route="fileupload", methods=['POST'])
```
After the authentication section, I add these lines to get a file from a post request and rename the file to "the original file name + 6 random characters"
```python
# Get file from request
logging.info("\nGetting file from POST request & renaming\n")
file = req.files['file']
original_name = file.filename
extension = os.path.splitext(original_name)[1]
# Appends random chars to filename
file_name = f"{os.path.splitext(original_name)[0]}-{uuid.uuid4().hex[:6]}{extension}" 
```
I also import `os`, and `uuid`
```python
import os, uuid
```
And then these lines to start the azure storage blob client and use it to upload the file.
```python
# Create blob client using local file name as blob name
blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)

# Upload created file
logging.info("\nUploading file & creating SAS token\n")
blob_client.upload_blob(file.stream, overwrite=True)
```

Testing this out, I can see my file get uploaded to my storage account. In the vs code terminal in the `backend` directory I run `func host start`. I then create a demo file and send it to the function URL with `curl`. 
```bash
┌──(clayton㉿Nucleus)──[12:25:10]──[~/ShipShape/backend]
└─$ func host start
Found Python version 3.11.2 (python3).

Azure Functions Core Tools
Core Tools Version:       4.0.5611 Commit hash: N/A +591b8aec842e333a87ea9e23ba390bb5effe0655 (64-bit)
Function Runtime Version: 4.31.1.22191

Functions:

        fileupload: [POST] http://localhost:7071/api/fileupload

┌──(clayton㉿Nucleus)──[12:25:10]──[~/ShipShape/backend]
└─$ echo 'testing123' > test.txt

┌──(clayton㉿Nucleus)──[12:26:17]──[~/ShipShape/backend]
└─$ curl -X POST -F "file=@test.txt" 'http://localhost:7071/api/FileUpload'
```
Checking the container after this I can see that my test file got renamed correctly and uploaded to the container.

Now I need to implement a function to generate an SAS token for this uploaded file. I need to import 3 more modules from `azure.storage.blob`:
```python
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
```
After the `app` line and before `@app.route` I add a function that will create an SAS token valid for one day. I don't add a `start_time` attribute because due to clock skew and timezone differences around the world, setting the start time to "now" can actually mean "later" somewhere else in the world. Not specifying the `start_time` means the SAS will token will be valid instantly after creation.

There are 2 ways you can authenticate an SAS token, with the storage account key, or with a user delegation key. A user delegation key is generally considered more secure as it doesn't require including a key anywhere in your code. A user delegation key will use Entra ID to authenticate to Azure either as my user (in local environment via Azure CLI) or as a managed identity (when deployed to Azure) to request a key to authenticate the SAS token. 

To create the UDK, I add a start time of 15 minutes ago (to account for clock skew) and an expiration of 1 minute. The UDK only needs to stay valid for as long as it takes to create the SAS token, so really I could probably give it an expiration time of 20 seconds or so and it would still work.
```python
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

@app.route(route="fileupload", methods=['POST'])
```
I then add these lines to print the SAS url. The `print` line will print the SAS url to the function output for testing, I'll remove this before deployment.
```python
# Upload created file
logging.info("\nUploading file & creating SAS token\n")
blob_client.upload_blob(file.stream, overwrite=True)

# Print SAS Token
sas_token = create_service_sas_blob(blob_client, blob_service_client, file_name)
sas_url = f"{blob_client.url}?{sas_token}"
print("\nSAS Token:\n", sas_url)

return func.HttpResponse(sas_url, status_code=200, headers={"Content-Type": "text/plain"})
```
Now I test this again by sending another `curl` request to the function, and this time I get back a URL with the SAS token!
```bash
┌──(clayton㉿Nucleus)──[12:36:50]──[~/ShipShape/backend]
└─$ curl -X POST -F "file=@test.txt" 'http://localhost:7071/api/FileUpload'

https://shipshapesa.blob.core.windows.net/fileshare/test-128733.txt?se=2024-04-20T19%3A02%3A11Z&sp=r&sv=2023-11-03&sr=b&skoid=4f3cf043-2002-41f1-852d-96d3d07e688f&sktid=727f911f-105f-4e72-ac9e-fac66a2efc00&skt=2024-04-20T18%3A46%3A11Z&ske=2024-04-20T19%3A02%3A11Z&sks=b&skv=2023-11-03&sig=wSyOIsjPSrzkNfcYFO4gEEOzzkbwJjKFnWRv27iz/sg%3D 
```
Browsing to the URL, my test file downloads
![download](2024-04-19_12-41.png)
My python script at this point looks like this:
```python
import os, uuid
import azure.functions as func
import logging
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
import datetime

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

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

@app.route(route="fileupload", methods=['POST'])
def fileupload(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("\nPython HTTP trigger function processed a request\n")

    try:
        logging.info("\nConnecting to Azure Blob Storage\n")
        
        # Connect to Blob Storage
        account_url = os.getenv('ACCOUNT_NAME')
        default_credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(account_url, credential=default_credential)
        container_name = os.getenv('CONTAINER_NAME')

        # Get file from request
        logging.info("\nGetting file from POST request & renaming\n")
        file = req.files['file']
        original_name = file.filename
        extension = os.path.splitext(original_name)[1]
        # Appends rand string to filename
        file_name = f"{os.path.splitext(original_name)[0]}-{os.urandom(6).hex()[:6]}{extension}" 

        # Create blob client using local file name as blob name
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)

        # Upload created file
        logging.info("\nUploading file & creating SAS token\n")
        blob_client.upload_blob(file.stream, overwrite=True)

        # Print SAS Token
        sas_token = create_service_sas_blob(blob_client, os.getenv('STORAGE_KEY'), file_name)
        sas_url = f"{blob_client.url}?{sas_token}"
        print("\nSAS Token:\n", sas_url)

        return func.HttpResponse(sas_url, status_code=200, headers={"Content-Type": "text/plain"})

    except Exception as ex:
        print('Exception:')
        print(ex)
```
## Hardening Function
Now, currently, any file type with any contents will be accepted by the function. There's no mime type checking, no file extension checking. There's also no checking for path traversal or command injection attacks in the name (like a file called `../../;rm -rf /;test.txt`). The only files that should be uploaded through this function are `.json` files, and anything else is likely an error or an attacker. So I need to add some file type checking and name sanitization.
### Check Extension
To check the file extension, I add these lines after getting and naming the file from the request. This will make sure that the filename *ends* with `.json`. Don't just use a `os.path.splitext(original_name)[1]` because that will only check that the second field is `.json`, and a file like `evil.json.exe` or something could get through. Also if possible, it's always safer to use a whitelist rather than a black list in this situation.
```python
file = req.files['file']
original_name = file.filename

# Check extension
if not original_name.lower().endswith('.json'):
	return func.HttpResponse("Only .json files are accepted", status_code=400)
```
After this I test it and any files that don't end in `.json` are rejected.
```bash
┌──(clayton㉿Nucleus)──[13:34:55]──[~/ShipShape/backend]
└─$ curl -X POST -F "file=@test.txt" 'http://localhost:7071/api/FileUpload'
Only .json files are accepted

┌──(clayton㉿Nucleus)──[13:34:55]──[~/ShipShape/backend]
└─$ curl -X POST -F "file=@test.json.txt" 'http://localhost:7071/api/FileUpload'
Only .json files are accepted
```
### Mime Type
To check mime type, I install `python-magic` in my environment and add it to `requirements.txt`. I import it at the top of the file with `import magic`. I then add these lines after getting the file and setting the original filename
```python
# Get file from request
logging.info("\nGetting file from POST request & renaming\n")
file = req.files['file']
original_name = file.filename

# Mime type check
mime = magic.Magic(mime=True)
# read first 2048 bytes to determine MIME
detected_mime = mime.from_buffer(file.stream.read(2048)) 
# Reset stream position after reading
file.stream.seek(0)
if detected_mime != 'application/json':
	return func.HttpResponse("File is not a valid JSON file", status_code=400)
```
And now If I create a file that has the `.json` extension, but does contain valid json, it will error.
```bash
┌──(clayton㉿Nucleus)──[13:36:39]──[~/ShipShape/backend]
└─$ echo 'testing123' > evil.json

┌──(clayton㉿Nucleus)──[12:57:23]──[~/ShipShape/backend]
└─$ curl -X POST -F "file=@evil.json" 'http://localhost:7071/api/FileUpload'
File is not a valid JSON file
```
I create a valid `test.json` file and send that, and the file uploads and I get my SAS token
```bash
┌──(clayton㉿Nucleus)──[12:55:32]──[~/ShipShape/backend]
└─$ echo '{"testing": "123"}' > test.json

┌──(clayton㉿Nucleus)──[12:56:30]──[~/ShipShape/backend]
└─$ curl -X POST -F "file=@test.json" 'http://localhost:7071/api/FileUpload'
https://shipshapesa.blob.core.windows.net/fileshare/test-8163b0.json?st=2024-04-19T19%3A57%3A23Z&se=2024-04-20T19%3A57%3A23Z&sp=r&sv=2023-11-03&sr=b&sig=lHYf5oXWcxFqOaV2fGD47a9GPo1kx1COyWBZ9CY4LpA%3D
```
### Sanitize Filename
Now I need to sanitize the file name from any path traversal or command injection attacks. For this I install`pathvalidate` and add it to `requirements.txt`. I'll use `pathvalidate` to sanitize the filenames and a `while` loop to remove any leftover dots. Don't just do something like `os.path.basename(original_name).replace('../', '')`, as that won't recursively remove the pattern. If a file has `....//` in its name, the first `../` will be removed, but a `../` will still be left over. At the top of the file I import it with
```python
from pathvalidate import sanitize_filename
```
To sanitize the filename I create  function outside of the try loop below my SAS function
```python
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
```
And then in the `try` loop I remove the previous extension and file_name variable and replace it with this line below the mime type check
```python
if detected_mime != 'application/json':
	return func.HttpResponse("File is not a valid JSON file", status_code=400)

file_name = sanitize_and_format_filename(original_name)
```
To test this, I proxy my curl request to Burpsuite with the `-x 127.0.0.1:8080` flag and try some malicious file names
```bash
curl -x 127.0.0.1:8080  -X POST -F "file=@test.json" 'http://localhost:7071/api/FileUpload'
```
All the files still get uploaded and a link gets generated, but the file names get properly sanitized.

![lfi](2024-04-19_14-05.png)

This is what my final file after the sanitization steps looks like
```python
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
```
# Integrate Function with HTML Site
Now that the function is working, I need to integrate it into my site. I need to edit the html and create some javascript that will send the file to the function, and print the returned SAS token to that webpage. I copy my `index.html` to a new file called `maintence.html`. I edit the html to include a upload form and button. I give the `input` the name `file`, which is what it's called in the function.
```html
<div class="detail-box">
  <h2>Upgrades & Maintence</h2>
  <form id="upload-form" enctype="multipart/form-data" class="upload-form">
	<p class="upload-msg">Upload your starship report here</p>
	<input type="file" name="file" id="starshipReport" required>
	<button type="submit" class="upload-btn">Upload Report</button>
	<p id="upload-instruct" class="upload-instruct">Your report will be sent to our
	 engineers andyou will recieve a time sensitive link to your report
	</p>
  </form>
</div>
```
For the javascript I create a script to listen for the html element `upload-form` and the `submit` event. It will grab the data from the `file` object and add it to a POST request that gets sent to the function URL. It then gets the data back from the function and overwrites the html element `upload-instruct` with the SAS token in the form of a download link.
```js
const localFunctionUrl = "http://localhost:7071/api/fileupload";

// upload.js
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('upload-form').addEventListener('submit', function(event) {
        event.preventDefault();

        const fileInput = document.getElementById('starshipReport');
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        // Display a loading message
        const instructElement = document.getElementById('upload-instruct');
        instructElement.innerHTML = "Report recieved. We are generating your link...";

        fetch(localFunctionUrl, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok: ' + response.statusText);
            }
            return response.text();
        })
        .then(data => {
            console.log('Success:', data);
            const instructElement = document.getElementById('upload-instruct');
            instructElement.innerHTML = `Access your uploaded file here: <a href="${data}" target="_blank">Download Link`;
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error uploading file.');
        });
    });
});
```
I also ass some CSS to style the download link to be bright green and to become underlined when the cursor hovers over it.
```css
#upload-instruct a {
    background: none;  /* No background */
    border: none;      /* No border */
    color: #00ff00;    /* Green text */
    padding: 0;        /* No padding */
    font-family: inherit; /* Inherits the font from the parent element */
    font-size: inherit; /* Inherits the font size from the parent element */
    display: inline;   /* Ensures it doesn't display like a block element */
    margin: 0;         /* No margin */
    cursor: pointer;   /* Shows a pointer on hover */
}
#upload-instruct a:hover {
  text-decoration: underline; /* This will underline the text on hover */
}
```
And the final result looks like this:

![sas](2024-04-19_17-07.png)

## Managed Identity
Now that the function is fully working locally, it's time to deploy it to Azure. I need to create a Function App. I'll then give that function app a managed identity with the *Storage Blob Data Contributor* role scoped to my *shipshapesa* storage account.

In the portal I go to *Function App > Create*. I select my ShipShapeRG resource group, give it the name *ShipShapeFA*. I select *python* for the runtime stack, *3.11* for the version, and select the region closest to me. I leave the OS as *Linux* and the hosting option as *Consumption.*

![fa](2024-04-19_18-00.png)
On the storage page I select my *shipshapesa* storage account. Everything else I leave as is and deploy the function app.
##### Best Practice Note:
Ideally, my storage account would be configured to exist inside a Vnet and only allow access from inside the Vnet and from my home IP address (for testing purposes). However, to [use a secured storage account with a function app]() requires [integrating the function with a vnet using a private endpoint](https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-vnet) which is only possible with the Functions Premium plan. Which will drive my cost up quite a bit. If this website or project was going to be larger scale or handle more situation, I would definitely set this up.

Now to set up the managed identity. Once the function app is deployed I hit *Go to Resource*. I then go down to *Identity*, and in the *System assigned* tab I flip the *status* slider to *On*, and then hit *Save*. After this I click *Azure role assignments*.

![id](2024-04-21_00-33.png)

I click *Add role assignment*. For the scope I select *storage*, I select my current subscription, I select the storage account that my files are uploaded to, *shipshapesa*, and select the *Storage Blob Data Contributor* role, and then hit *Save*. After a little bit I hit refresh and see my new role assignment listed.

![rbac](2024-04-19_19-13.png)

Back in VS Code I right click on my `api` directory and select *Deploy to function app*

![deploy](2024-04-21_00-34.png)

I select my subscription, I select my *ShipShapeFA* Function App, and wait for it to deploy. After this is done I open the command palette with F1 and type *Azure Functions: Upload Local Settings*. This will take all the environment variable currently in my `local.settings.json` file and upload them to the environment variables of the Function App. I select my subscription and my *ShipShapeFA* function app, and wait for the settings to deploy.
## CI/CD Pipeline
So now I've got the function deployed. Lovely. But, what if I need to make some changes to it? I could create the changes locally and manually deploy it to the Function App, but there's a better way. I'm going to integrate the azure function with a [Github Workflow](https://docs.github.com/en/actions/using-workflows/about-workflows). Github will give me version control over the changes I make, and a workflow can be configured in Github where when I push a change to my repo, the same changes will be deployed to Azure.

**CI/CD** stands for **C**ontinuous **I**ntegration **C**ontinuous **D**eployment. There are 4 major sections to this process.

1. **Version Control** - A tool like [Github Workflows](https://docs.github.com/en/actions/using-workflows/about-workflows) is used to track and manage changes made to the code
2. **Continuous Integration** - The code in version control (Github in this example) will be built, integrated, and tested in the current environment (Azure)
3. **Continuous Delivery** - Once the code has passed those tests it will be placed in a staging area where it is ready to pushed to production. Usually someone will have to go in and manually deploy this to production
4. **Continuous Deployment (optional)** - This is an optional step where once code that has passed every test enters the staging area, it will automatically be pushed to production.
## Backend Workflow
So, to get this set up I'll first create a Github workflow that will deploy changes to Azure when a change is made to the `backend` directory. In the top directory of my project, I create a folder called `.github`, in there I create a directory called `workflows`, and in there I create a file called `backend.main.yaml`. 

Now I need to create a service principal and save the secret info to a Github Actions Secret. A service principal is basically an identity used by apps, services, and automation tools used to access specific resources. It's like a username and password/certificate, but for an application instead of a person. This service principal will have `Contributor` privileges over my `ShipShapeRG` resource group. **This is a sensitive piece of data, be careful with it.***
```bash
┌──(clayton㉿Nucleus)──[11:00:53]──[~/ShipShape/frontend]
└─$ az ad sp create-for-rbac --name ShipShapeDeploy --role contributor --scopes /subscriptions/<SUBSCRIPTION ID>/resourceGroups/ShipShapeRG --json-auth
Creating 'contributor' role assignment under scope '/subscriptions/<SUBSCRIPTION ID>/resourceGroups/ShipShapeRG'
The output includes credentials that you must protect. Be sure that you do not include these credentials in your code or check the credentials into your source control. For more information, see https://aka.ms/azadsp-cli
{
  <REDACTED>
}
```
I copy the `json` output of the command and go to my Github repo and click *Settings.* I go to *Secrets and Variables > Actions* and create a new Action Secret called `AZURE_CREDENTIALS`. I paste in the `json` output of the command and add the secret.

![secret](2024-04-21_11-31.png)

I grab the `yaml` from [this page of Microsoft documentation](https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-github-actions?tabs=linux%2Cpython&pivots=method-manual#example-workflow-configuration-file) and modify it. In the `on` section I set this workflow to only run when a `push` is made that includes anything in the `backend` directory. I change AZURE_FUNCTIONAPP_NAME to the name of my Function App. I add a step to login to azure with azure CLI using the creds stored in a github secret. In the `Resolve Project Dependencies Using Pip` section, I add a `/api` section at the of the `pushd` line to make sure the script is in the proper directory when it runs `pip`.  The `package` line points to where your function actually lives and so I change that line to `package: ${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}/api`.
```yml
name: Deploy_backend

on:
  push:
    branches: [ master ]
    paths:
    - 'backend/**'

env:
  AZURE_FUNCTIONAPP_NAME: 'ShipShapeFA'           # set this to your function app name on Azure
  AZURE_FUNCTIONAPP_PACKAGE_PATH: 'backend'       # set this to the path to your function app project, defaults to the repository root
  PYTHON_VERSION: '3.11'                          # set this to the python version to use (e.g. '3.6', '3.7', '3.8')

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    environment: dev
    steps:
    - name: 'Checkout GitHub Action'
      uses: actions/checkout@v3
    
    - name: 'Login via Azure CLI'
      uses: azure/login@v1
      with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

    - name: Setup Python ${{ env.PYTHON_VERSION }} Environment
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: 'Resolve Project Dependencies Using Pip'
      shell: bash
      run: |
        pushd './${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}/api'
        python -m pip install --upgrade pip
        pip install -r requirements.txt --target=".python_packages/lib/site-packages"
        popd

    - name: 'Run Azure Functions Action'
      uses: Azure/functions-action@v1
      id: fa
      with:
        app-name: ${{ env.AZURE_FUNCTIONAPP_NAME }}
        package: ${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}/api
        publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE }}
        scm-do-build-during-deployment: true
        enable-oryx-build: true
```
Once this is done, I commit and push my project
```bash
git add -A
git commit -m "<MESSAGE>"
git push
```
After this I can hop onto github and go to the *Actions* tab of my repo, and see my action being run. Great! Now I can edit my function locally, and whenever I push a change to Github, my azure deployment will also be updated.

![action](2024-04-21_11-55.png)

Now that my function is deployed, I change the line in my `upload.js` file to use the new function URL. I go into the Azure Portal and go to *Function Apps > {FUNCTION APP NAME}  > {FUNCTION NAME}* and click *Get Function Url*. I then paste this into `upload.js`

![url](2024-04-21_12-19.png)
# Deploy Website
Now that my function is fully deployed and set up wit a CI/CD pipeline, it's time to deploy my site to an Azure Static Web app and set up a CI/CD pipeline for it.

On the Azure Portal, I go to *App Services > Create > Static Web App*. I select my resource group, give it a name, select the *Free* hosting plan. I select my *ShipShape* github repository and the correct branch. I select the *HTML* build preset, and tell it that my app is located in `/frontend`. In the *Advanced* tab I select the location closest to me. After that I create it and wait for it to deploy.

![swa](2024-04-21_12-42.png)

Once deployment is complete, I can go to the resource and click on the URL, and I'm taken to my site. And look at that we're live!

![live](2024-04-21_12-59.png)

Checking my github repo, I can see that a new workflow file was created and that an action has been run

![workflow](2024-04-21_13-00.png)

![action](2024-04-21_13-01.png)

To update my local repo with the remote one, I run a git pull. I now have the workflow file on my local machine. Now whenever I make a change to the frontend of my site, it was also automatically be deployed to Azure. To test this out, I add a exclamation mark after `Welcome to ShipShape!` and run a `git push`. Sure enough, my static web app on azure gets this change as well.

![success](2024-04-21_13-08.png)

Great! Now I have this site fully functioning. I can make changes to the front and backend locally, push them to Github, and the deployment in Azure will be updated as well.
# Create Logic App to Parse uploaded files
The next feature I would like to implement is when a file is uploaded through the site, the file is parsed and the repairs and supplies needed are sent to the proper locations. To do this, I'll use a Logic App triggered by an HTTP request. I can then modify my function to send the uploaded file to the Logic App as well as blob storage. The logic app can then parse the `json` and send the info in an email to the proper locations.

First off, I create a Logic App. I search for *Logic App* in the portal and select *Create*. I select my resource group, give it a name, select the location closest to me, I enable log analytics, and choose the consumption plan.

![logic app](2024-04-21_14-42.png)

After creation, I go into the Logic App and select *Logic App Designer*, I click on *Add a trigger* and search for "http" and select the trigger option for *"When an HTTP request is received"*

![LAW](2024-04-21_14-59.png)

I change the method to POST. Then I click the option to *"Use sample payload to generate schema"* This will allow to me to upload a sample `json` file that should be sent to the Logic App and a `json` schema will be automatically generated. I paste in this sample `json` payload. After that I hit save in the function app designer.
```json
{
    "ShipName": "CosmicCommander",
    "Repairs Needed": {
        "Thrusters": true,
        "Blast Shield": true,
        "Landing Gear": true,
        "Warp Drive": true,
        "Radar": true
    },
    "Supplies Needed": {
        "Rations": "12",
        "Laser Crystals": "3",
        "Droid Silicon": "6",
        "Capacitors": "27",
        "Fuel (Liters)": "275"
    }
}
```
Opening up the HTTP trigger again I see the HTTP url. Now I should be able to send my `json` payload here and see it in the logic app.

After this I add the action *"Send an email (V2)"*  through Outlook.com (not Office 365 Outlook). I link to my Outlook account by logging in. For this project I will just be using my personal Outlook email. For the configuration of the action, I configure the email to be sent to my personal Gmail, however the email can be sent to any email address. I then use the lightning icon to add in fields from the previous step to configure an email. After this I hit save.

![send email](2024-04-21_15-39.png)

I should now be able to send a `json` file to the logic app, and it should send me an email with the information.
```bash
curl -X POST -H 'Content-Type: application/json' -d @ship-report.json '<LOGIC APP URL>'
```
After this, a second or 2 later, I hear the email ping on my phone! Checking my inbox, I see an email with all the `json` info properly formatted.

![email](2024-04-21_15-57.png)

Now I just need to add this functionality into my function and redploy it. I add a new chunk below the SAS token section in my function. This snippet resets the data stream to the beginning of the. It then retrieves the Logic App URL from an environment variable in `local.settings.json`. It then sends the uploaded `json` file to the Logic App. The Logic App gives a 202 response if it receives data successfully, and so if the function doesn't receive a 202 back, it will throw an error.
```python
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
```
I start up the function locally and send it the file in a POST request. I get back my SAS URL, and in my inbox I receive an email
```bash
┌──(clayton㉿Nucleus)──[16:24:50]──[~/test]
└─$ curl -X POST -F "file=@ship-report.json" http://localhost:7071/api/fileupload

https://shipshapesa.blob.core.windows.net/fileshare/ship-report-08207f.json?se=2024-04-21T23%3A25%3A56Z&sp=r&sv=2023-11-03&sr=b&skoid=4f3cf043-2002-41f1-852d-96d3d07e688f&sktid=727f911f-105f-4e72-ac9e-fac66a2efc00&skt=2024-04-21T23%3A09%3A56Z&ske=2024-04-21T23%3A25%3A56Z&sks=b&skv=2023-11-03&sig=BtCj5PNMjFzJYeSijY2ny5fhKBFpyCQY3FZI2OHvgDE%3D 
```

![email](2024-04-21_16-25.png)

Now that this is working, I deploy the function to azure by running a git push
```bash
git add -A
git commit -m "Integrate logic app into function"
git push
```
I also add the logic app url environment variable to azure with the command pallet (F1) and typing *Azure Functions: Upload Local Settings*. Once the updated function is live, I go to the website, upload the ship report, and I get a working SAS URL, and an email. 
# VM Deployment
For demonstration purposes, I want to set up automatic Vnet deployment and Virtual Machine creation. When the `.json` file is uploaded, if anything in the `"Repairs Needed"` section is set to `true`, I want to deploy a virtual network. For every field set to `true` in the `Repairs` section, I want a subnet and VM deployed. My plan here is to create separate ARM templates, one for deploying the Vnet and NSG, and one for each of the VMs and Subnets. I'll host the files in a Github repo (to make it easy to make changes), and call the files with a my Logic App. I'll set up some logic in the logic app that will determine which bicep files to call.
## Network Bicep File
To give me a starting point I create a VM in the Azure Portal, complete with a new Vnet and NSG. On the last screen I select *Download Template.* I select the Standard_B1ls VM size which is the smallest size. I only need these VMs to pop up for a second, perform a simple task, and shut down, so I go with the cheapest option. On the *Disks* page I go with a *Standard SSD*.

![basics](2024-04-23_10-48.png)

On the *Networking* page I create a new Vnet with the address range `10.10.0.0/16`, and a Subnet with the address range `10.10.1.0/24`

![networking](2024-04-23_10-51.png)

I create a new NSG and a rule to allow SSH access from my IP only. I also add a rule to allow ICMP requests from my machine only

![ssh](2024-04-23_10-52.png)

Everything I else I leave alone and on the *Review + Create* page, I click *Download a template for automation* in the lower right corner

![download](2024-04-23_10-54.png)

I open up the `template.json` file in VS Code and right click it and select *"Decompile Into Bicep"* to generate a `.bicep` version of the template.

![bicep](2024-04-23_10-55.png)

I split the file into 2 sections, one for deploying the Vnet and NSG, and one for  deploying the VM and its required resources.

At the top of the Networking file, I set the parameters and variable I'm going to need. I use `var` for the values that I know I don't want to change.
```json
@secure()
param localIP string
param location string = resourceGroup().location

var vnetName = 'VmFleetVnet'
var nsgName = 'VmFleetNSG'
var vnetAddressPrefix = '10.10.0.0/16'
```
`localIP` is my home IP address for use in the NSG creation. I pass this with the `@secure()` decorator. This means Azure will avoid logging this value and it won't be displayed to the command line. I will store this value in an Azure Key Vault and use a `bicepparam` file to call the value when the deployment is run.

`location` sets the location for the resources to be created in, in this case it will take the same location as their parent resource group

`vnetName` sets the name of the Vnet, and `nsgName` sets the name for the NSG.

`vnetAddressPrefix` sets the address space of the virtual network.

After this is the NSG deployment.
```json
resource networkSecurityGroup 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowSshIn'
        properties: {
          priority: 100
          protocol: 'TCP'
          access: 'Allow'
          direction: 'Inbound'
          sourceApplicationSecurityGroups: []
          destinationApplicationSecurityGroups: []
          sourceAddressPrefix: localIP
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '22'
        }
      }
      {
        name: 'AllowIcmpIn'
        properties: {
          priority: 200
          protocol: 'ICMP'
          access: 'Allow'
          direction: 'Inbound'
          sourceApplicationSecurityGroups: []
          destinationApplicationSecurityGroups: []
          sourceAddressPrefix: localIP
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}
```
This is left mostly the same from the template download except that I change `sourceAddressPrefix` to `localIP`.

And last is the Vnet Creation.
```json
resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
  }
}
```
For the Vnet creation I remove the `subnets` section as I want to determine what specific subnet to create based on what was set to `true` in my json file, and so I'll leave subnet creation to my VM creation files.

Next I right click on the bicep file and select *"Generate Parameters File"*, I select the *bicepparam* type and tell it to only create parameters for the required fields. This creates a `bicepparam` file with just one field, `localIP`. I use the [getSecret](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/bicep-functions-parameters-file) function to pull a secret from my Key Vault. This function takes 4 arguments, the subscription ID, the resource group, the key vault name, and the secret name. I haven't created my Key Vault yet but these are the values I'll use when I do.
```json
using './NetworkDeploy.bicep'

param localIP = getSecret('<SUBSCRIPTION ID>', 'VmFleetRG', 'VmFleetKV', 'LocalIp')
```

Next up is the VM deployment. Again at the top of my file I set my parameters and variables.
```json
var vmName = 'Red1'
param adminUsername string = 'Red1'
@secure()
param sshPublicKey string
var vnetName  = 'VmFleetVnet'
var subnetName = '${vmName}Subnet'
var subnetAddressPrefix = '10.10.1.0/24'
param location string = resourceGroup().location
var publicIPAddressName = '${vmName}PublicIP'
var unique = uniqueString(vmName, resourceGroup().id)
var domainNameLabel = '${toLower(vmName)}-${replace(toLower(unique), '-', '')}'
var nicName = '${vmName}Nic'
var nsgName = 'VmFleetNSG'
var nsgId = resourceId('Microsoft.Network/networkSecurityGroups', nsgName)
var vmSize = 'Standard_B1ls'
var osDiskType = 'Standard_LRS'
var linuxConfiguration = {
  disablePasswordAuthentication: true
  ssh: {
    publicKeys: [
      {
        path: '/home/${adminUsername}/.ssh/authorized_keys'
        keyData: sshPublicKey
      }
    ]
  }
}
```
`vmName` and `adminUsername` are the name for the VM and admin user. `adminUsername` is set as a parameter because [as per this page](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/linter-rule-admin-username-should-not-be-literal) the `adminUsername` in VM creation can't be set to a literal value and has to be a parameter.

`sshPublicKey` is passed as a `@secure` parameter, and I will also be storing this in a key vault and grabbing the value with the `bicepparam` file. Technically an SSH public key isn't exactly the most secure of information, as it is literally meant to be public. But I wanted to get some more experience with Key Vault, so I decided to throw it in there.

`vnetName`, `subnetName` and `subnetAddresPrefix` are all used to set their respective values.

For `location` I use the resource group location again. This must be a parameter because [`resourceGroup()` has to be used in a parameter](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/linter-rule-no-loc-expr-outside-params) and can't be used in a variable

`publicIPAddressName` will be used to name the public IP, and is named dynamically based on the VM name.

`nsgId` is used to grab the ID of the NSG deployed in the Networking bicep file which is needed when setting up the network interface down the line.

`uniqueString` and `domainNameLabel` are used to set a unique name for DNS to use when creating the public IP address. The format of this name has to be all lowercase, no slashes, and alphanumeric. I use the `uniqueString` function to generate a hash based on the `vmName` and the resource group id. I then use `toLower` in the next section to make sure everything is lower case and `replace` to replace any slashes with nothing.

`nicName` sets the name of the network interface based on the VM name

`nsgName`, `vmSize`, and `osDiskType` are all used to set their values for later use

`subnetAddressPrefix` sets the address space of the subnet

`linuxConfiguration` sets values that will be used down the line when configuring the VM. Password Authentication is set to off, so that only SSH access will be allowed. The path to store my public SSH on the VM is set with `path`. And the public key to be stored there is set with `keyData` and will be my public SSH key.

After this I declare the Vnet to use and deploy a subnet
```json
resource existingVnet 'Microsoft.Network/virtualNetworks@2023-09-01' existing = {
  name: vnetName
}

resource subnet 'Microsoft.Network/virtualNetworks/subnets@2023-09-01' = {
  parent: existingVnet
  name: subnetName
  properties: {
    addressPrefix: subnetAddressPrefix
  }
}
```
`existingVnet` will reference the Vnet that was set up by the Networking `bicep` file. `subnet` then deploys a subnet to that Vnet with the name and address space specified in variables

Next I set up the Public IP Address
```json
resource publicIPAddress 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: publicIPAddressName
  location: location
  properties: {
    publicIPAllocationMethod: 'Dynamic'
    publicIPAddressVersion: 'IPv4'
    dnsSettings: {
      domainNameLabel: domainNameLabel
    }
  }
  sku: {
    name: 'Basic'
  }
}
```
I give it the `name`, `location`, and randomized `domainNameLabel` as specified in my variables. I leave it at `Dynamic` allocation method and `IPv4` address version. I also set the `sku` to `Basic`.

After this is the Network Interface
```json
resource networkInterface 'Microsoft.Network/networkInterfaces@2023-09-01' = {
  name: nicName
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: {
            id: publicIPAddress.id
          }
          subnet: {
            id: subnet.id
          }
        }
      }
    ]
    networkSecurityGroup: {
      id: nsgId
    }
  }
}
```
I specify the ID's of the Public IP address and the subnet for the nic to attach to, as well as the ID of the NSG to be assigned to the subnet.

And finally is the VM deployment
```json
resource virtualMachine 'Microsoft.Compute/virtualMachines@2023-09-01' = {
  name: vmName
  location: location
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    storageProfile: {
      osDisk: {
        createOption: 'fromImage'
        managedDisk: {
          storageAccountType: osDiskType
        }
        deleteOption: 'Delete'
      }
      imageReference: {
        publisher: 'debian'
        offer: 'debian-11'
        sku: '11-gen2'
        version: 'latest'
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: networkInterface.id
          properties: {
            deleteOption: 'Delete'
          }
        }
      ]
    }
    additionalCapabilities: {
      hibernationEnabled: false
    }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: linuxConfiguration
    }
    securityProfile: {
      securityType: 'TrustedLaunch'
      uefiSettings: {
        secureBootEnabled: true
        vTpmEnabled: true
      }
    }
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: true
      }
    }
  }
}
```
The name, location, size, admin username, and disk type are pulled from my variables. `deleteOption`  in `managedDisk` and `networkInterfaces` specifies that if the VM is deleted, its associated NIC and disk will be deleted as well. I set `networkInterfaces` to the ID of the previously deployed network interface. `linuxConfiguration` refers back to the variable I set up. I leave the `securityProfile` as is with secure boot and TPM enabled. I also leave boot diagnostics enabled.

Once this is done I right click the `Red1Deploy.bicep` file and select *Generate Parameter File* and select the `bicepparam` type, generate only the required paramters. Again, this gives me a param file with only one line for `sshPublicKey`
```json
using './Red1Deploy.bicep'

param sshPublicKey = getSecret('<SUBSCRIPTION ID>', 'VmFleetRG', 'VmFleetKV', 'SSH-Public-Key')
```
I use `getSecret` and enter my subscription id, the resource group of the vault, the name of the key vault, and the name of the secret.
### Deploy Key Vault
After this I need to set up my Key Vault to store my IP address and my public SSH key. I hop into the Azure Portal and search for *Key Vaults* and click on *Create*. I put it in my *VmFleetRG* resource group, give it a name, and choose the closest location to me.

![kv](2024-04-24_01-01.png)

On the *Access Configuration* page I leave the permission model on RBAC, and check the box give Azure Resource Manager access to the vault for template deployment. After this I hit *Review + Create.*

![access](2024-04-24_01-02.png)

Once this is deployed, I hop into the Access control(IAM) section and add a role. I assign the *Key Vault Secrets Officer* role to myself which will allow me to write new secrets. After that I go to the *Secrets* section and add 2 secrets, one containing my IP address, and one containing my public SSH key.

![kv](2024-04-24_01-19.png)

Now, I should be able to test my deployment files. I run a command to first deploy the networking file, and then the vm file.
```bash
┌──(clayton㉿Nucleus)──[0:55:01]──[~/GitRepos/VMFleetCommander]
└─$ az deployment group create -g VmFleetRG --template-file NetworkDeploy/NetworkDeploy.bicep -p NetworkDeploy/NetworkDeploy.bicepparam && \
cmdand> az deployment group create -g VmFleetRG --template-file Red1/Red1Deploy.bicep -p Red1/Red1Deploy.bicepparam
```

I give it a bit to deploy, and once it's done I can see all my resources in the Azure Portal!

![rg](2024-04-23_11-41.png)

After this I can can grab my VM's IP address and SSH into it. I also check that I'm able to ping the VM.
```bash
┌──(clayton㉿Nucleus)──[11:39:06]──[~/GitRepos/VMFleetCommander]
└─$ ssh -i ~/.ssh/id_rsa Red1@<REDACTED>

<...SNIP...>

Red1@Red1:~$ id
uid=1000(Red1) gid=1000(Red1) groups=1000(Red1),4(adm),20(dialout),24(cdrom),25(floppy),27(sudo),29(audio),30(dip),44(video),46(plugdev),113(netdev)
Red1@Red1:~$ exit
logout
Connection to <REDACTED> closed.

┌──(clayton㉿Nucleus)──[11:44:27]──[~/GitRepos/VMFleetCommander]
└─$ ping <REDACTED>
PING <REDACTED> (<REDACTED>) 56(84) bytes of data.
64 bytes from <REDACTED>: icmp_seq=1 ttl=48 time=15.0 ms
```
After this I copy my `Red1Deploy.bicep` file 4 times. I change the `vmName`, `adminUsername`, and `subnetAddressPrefix` values.  Once I've updated all these files, I run the command to deploy all 5 subnets and VMs.
```bash
┌──(clayton㉿Nucleus)──[0:55:01]──[~/GitRepos/VMFleetCommander]
└─$ az deployment group create -g VmFleetRG --template-file NetworkDeploy/NetworkDeploy.bicep -p NetworkDeploy/NetworkDeploy.bicepparam && \                                                                                                           
cmdand> az deployment group create -g VmFleetRG --template-file Red1/Red1Deploy.bicep -p Red1/Red1Deploy.bicepparam  && \
cmdand cmdand> az deployment group create -g VmFleetRG --template-file Blue2/Blue2Deploy.bicep -p Blue2/Blue2Deploy.bicepparam && \
cmdand cmdand cmdand> az deployment group create -g VmFleetRG --template-file Green3/Green3Deploy.bicep -p Green3/Green3Deploy.bicepparam && \
cmdand cmdand cmdand cmdand> az deployment group create -g VmFleetRG --template-file Purple4/Purple4Deploy.bicep -p Purple4/Purple4Deploy.bicepparam && \
cmdand cmdand cmdand cmdand cmdand> az deployment group create -g VmFleetRG --template-file Black5/Black5Deploy.bicep -p Black5/Black5Deploy.bicepparam
```
And sure enough, they all run and I can see them in the Portal

![portal](2024-04-24_01-30.png)

Now that everything is working, I'll build all these bicep files into ARM templates, essentially converting them back into `json`. Why bother building them in `bicep` if they're just going to converting them back to `json`? Because `bicep` is much easier to construct these templates with, but ARM doesn't accept bicep files, it needs to be in the format of a `json` arm template. 

To convert my `NetworkDeploy.bicep`, in VS Code I right click my the file and select *Build ARM Template*. This gives me a `NetworkDeploy.json` file.

![](2024-04-24_12-32.png)

After that I right click `NetworkDeploy.bicepparam` and select *Build Parameters File*

![](2024-04-24_12-33.png)

I get 2 errors in my `NetworkDeploy.json` file, which is that the API version is not valid. I update it to the latest valid API. 

![](2024-04-24_12-34.png)

I also  get a notification from the [Snyk extension](https://marketplace.visualstudio.com/items?itemName=snyk-security.snyk-vulnerability-scanner) that any storage devices attached to the VM will not be encrypted at rest. To fix that I add a line to the `securityProfile`.

![](2024-04-24_12-37.png)

```json
        "securityProfile": {
          "encryptionAtHost": true, // Encrypt os disk at rest
          "securityType": "TrustedLaunch",
          "uefiSettings": {
            "secureBootEnabled": true,
            "vTpmEnabled": true
          }
        },
```

I repeat this process for all of `bicep` and `bicepparam` files, correcting the API version where necessary and updating the security profile. After this is done, I push to my ARM template Github repo.
## Logic App
Now, I need to set up my logic app to deploy a selection of these files based on the `json` payload it receives. To do this, I'll set up some logic in my logic app, and I'll use ARM actions to retrieve and deploy the templates in my repo. I hop back into the logic app I created earlier to send an email. I add a chain of `condition` actions.

![logic app](2024-04-24_13-28.png)

The first condition is an OR statement that says if Thrusters *or* Blast Shield *or* Landing Gear *or* etc. is true, to use ARM to deploy the Networking bicep file. If they are all false, do nothing.

![first con](2024-04-24_13-29.png)

The `true` statement leads into the *Create or update a template deployment* action from ARM. For this I set the subscription and resource group and give the deployment a name. For *Template URI* and *Parameters URI* I point it to the corresponding files in my Github Repo. I leave *Deployment Mode* at *Incremental*. I change *Wait for Deployment* to *Yes*. This means that the Logic App will wait to move on to the next action until the deployment is complete. This is important as all my VM & Subnet deployments depend on the Vnet and NSG being fully deployed.

![cond1](2024-04-24_13-29_1.png)

The ARM NetworkDeploy action leads into another `condition` action that states if `Thrusters` is `true`, to use ARM to deploy the template for the Red1 subnet and VM

![cond](2024-04-24_13-30.png)

For the ARM action, I point it to the corresponding template and parameter files. This time I leave *Wait for Deployment* as *No* because the other VMs and subnets don't depend on this deployment to work.

![red1](2024-04-24_13-30_1.png)

From the bottom plus sign of the condition statement (*not* the plus sign below the ARM action) I add another `condition` action. This is because if `Thrusters` is set to false, but `Blast Shield` is set to true, I want to `Blue2` to deploy even though `Red1` didn't. If I set the `condition` action from the plus sign of the Red1 ARM deployment, then if `Thrusters` is set to `false` and therefore didn't deploy `Red1`, then `Blue2` and none of the other subnets and VMs will deploy.

![](2024-04-24_13-31.png)

I add another ARM deploy action and point it to the `Blue2` template and parameters file, leaving the rest of the settings the same as the `Red1` deployment. I repeat this process out to `Black5`.

Once this is completed, I test out the Logic app by sending a `json` payload to the Logic App URL. I set alternating true and false values to the repair values. I grab the URL from the HTTP trigger function
```json
// test-payload.json
{
    "ShipName": "CosmicCommander",
    "Repairs Needed": {
        "Thrusters": true,
        "Blast Shield": false,
        "Landing Gear": true,
        "Warp Drive": false,
        "Radar": true
    },
    "Supplies Needed": {
        "Rations": "12",
        "Laser Crystals": "3",
        "Droid Silicon": "6",
        "Capacitors": "27",
        "Fuel (Liters)": "275"
    }
}
```
```bash
curl -X POST -H 'Content-Type: application/json' -d @test-payload.json '<LOGIC APP URL>' -k
```

After sending my payload, I go to the *Runs History* section and I can refresh the run and watch it make its way through all the different conidtions.

![](2024-04-24_13-34_1.png)

Going to my resource group's deployment page, I can see that the network was successfully deployed and the VMs and subnets are in the process of deploying.

![](2024-04-24_13-34.png)

After awhile, all the proper resources appear in my resource group

![](2024-04-24_13-36.png)

I grab the IP of Green 3 and I'm able to SSH into it
```bash
┌──(clayton㉿Nucleus)──[13:37:27]──[~/GitRepos/VMFleetCommander]
└─$ ssh -i ~/.ssh/id_rsa Green3@<REDACTED>

<...SNIP...>

Green3@Green3:~$ id
uid=1000(Green3) gid=1000(Green3) groups=1000(Green3),4(adm),20(dialout),24(cdrom),25(floppy),27(sudo),29(audio),30(dip),44(video),46(plugdev),113(netdev)
Green3@Green3:~$ exit

┌──(clayton㉿Nucleus)──[13:39:25]──[~/GitRepos/VMFleetCommander]
└─$ ping <REDACTED>
PING <REDACTED> (<REDACTED>) 56(84) bytes of data.
64 bytes from <REDACTED>: icmp_seq=1 ttl=47 time=19.3 ms
```
I rerun this deployment a few times to make sure everything is working as expected. I actually hit a weird error originally for a `RetryableError`. There wasn't any info on it on the [common deployment errors page](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) and the error came with not much info. This was when i changed the *Wait for Deployment* option in the *Network Deployment* action to *Yes*. I think what happened is that the logic app moved on to deploying the Red1 subnet and VM before the Vnet and NSG were live, and that caused the subnet to throw an error. After changing this value, I haven't gotten the error again.

Now to make sure the whole system is working, I upload the payload file to my static web app upload form. This should send the file to my Function App, which will also send the file to my Logic app. And I should end with the file in blob storage, an SAS URL to that file, an email with the file contents to my email, and a Vnet, and 3 subnets and VMs in that Vnet. I run it, and sure enough everything happens as it should.

Awesome! Everything's working. My ARM templates are able to access my Key vault, the logic app is able to parse my payload and access the proper templates, and all my templates are hosted on Github making modification easy.

# SQL Server & ShipeShape Store
The next thing I want to set up is a storefront. I want to host a small storefront on the website containing 5 items. This storefront will be connected to an SQL database that containing the inventory amounts for these items. When a user places an order, the corresponding SQL database value will be decremented by the amount ordered. The site should then be updated to reflect this value.
## Deploy SQL Server and Database
The first thing I need to do is set up an SQL server. To do this, in the Azure Portal I search for *Azure SQL*, select *Create* and then. select the *SQL databases* and *Single database* option

![](2024-04-24_16-37.png)

I create a new resource group called ShipShapeSQL, and I create a new SQL server. I give it a name, place it in the closest region to me, and select *"Use Microsoft Entra-only authentication* for the authentication method. I create a new user called `SqlAdmin` to be the Entra ID admin.

![](2024-04-26_00-00.png)

Back in database creation, I select the *Development* workload environment. This will just set a lower powered preset for the *Compute + storage* section. For back up redundancy I leave it at *Locally-redundant* to save costs. If this was a more critical SQL server, I would choose Geo-redundant for data safety.

![](2024-04-25_15-08.png)

On the *Networking* page, I select public endpoint, and flip the sliders to allow Azure Resources to access the server, as well as add my IP address to the firewall rules.

![](2024-04-24_16-40.png)

On the *Security* page, I enable Ledger. I also enable server-level encryption keys.

![](2024-04-24_16-46.png)

For configuring the ledger, I *Enable for all future tables*. I use Azure storage for storing the ledger (to save costs), and create a new storage account for this purpose. After this, I hit *Review + Create* and wait for it to deploy. The [Ledger](https://learn.microsoft.com/en-us/sql/relational-databases/security/ledger/ledger-overview?view=sql-server-ver16) is a security feature that preserves historical data. It keeps a record of all updates to a database and maintains the previous value in the ledger. It provides a chronicle of all changes made to a database over time.

![](2024-04-24_16-43.png)

After this I install [Azure Data Studio](https://learn.microsoft.com/en-us/azure-data-studio/download-azure-data-studio?tabs=linux-install%2Cwin-user-install%2Cubuntu-install%2Cwindows-uninstall%2Credhat-uninstall) which will allow me to connect to and interact with the SQL server from my home computer. I go into the newly deployed database and click, *Open Azure Data Studio*, this provides me a connection link and pops open Azure Data Studio. I use the SqlAdmin Entra ID credentials to connect.

![](2024-04-24_23-22.png)

![](2024-04-24_23-22_1.png)

Once connected, i open the `ShipShapeDB` database, and right click the `Tables` folder and select *New Table*.

![](2024-04-25_15-18.png)

I add 3 columns to the table, `id`, `item_name`, and `stock`. For the type I leave `id` and `stock` as `int`, and I change `item_name` to `nvarchar(255)` to allow alphabetical names. After this I name the table and click the *Publish Changes...* button.

![](2024-04-25_15-25_1.png)
Next I need to create 2 new database users with permissions to read and write data. I'll create one for my function app's managed identity, and one for my user account (for local testing purposes.) I right click on *ShipShapeDB* and select *New Query*. I switch the database from *master* to *ShipShapeDB* and enter the `CREATE USER` and `ALTER ROLE` commands. Make sure you are connected with Entra ID credentials, otherwise this will fail.

![](2024-04-25_15-29.png)

## Connect Function App to SQL
Now that the database is set up, I need to create a new Function that will connect with the database. The purpose of this function will be to update the site on pageload with the current stock of all the items. It will also be to submit orders to the database and decrement the database value, and then update the site with the new value.

In the VS Code Azure extension, I go into my `backend/api` directory and create a new folder called `Order`. In it, I create a new `__init__.py`, and a `function.json` file. I grab the contents of my `function.json` file from the FileUpload function and copy them over and add GET to `methods`. My new file structure looks like this:
```bash
.
├── FileUpload
│   ├── function.json
│   ├── host.json
│   ├── __init__.py
│   └── __pycache__
│       └── __init__.cpython-311.pyc
├── host.json
├── local.settings.json
├── Order
│   ├── function.json
│   └── __init__.py
│ 
├── __pycache__
│   └── function_app.cpython-311.pyc
└── requirements.txt
```
And `function.json` looks like this:
```json
{
    "scriptFile": "__init__.py",
    "bindings": [
      {
        "authLevel": "anonymous",
        "type": "httpTrigger",
        "direction": "in",
        "name": "req",
        "methods": [
          "get",
          "post"
        ]
      },
      {
        "type": "http",
        "direction": "out",
        "name": "$return"
      }
    ]
  }  
```
After this I hop into `__init__.py` and add the imports I'm going to need and the connection string. 
```python
import os
import logging
import pyodbc
import azure.functions as func
import json

connection_string = os.getenv('SQL_CONN_STR')
```
I add a line for the connection string in my `local.settings.json`
```json
"SQL_CONN_STR": "<CONNECTION STRING>"
```

To get the connection string I navigate into my ShipShapeDB SQL database and go to *Connection Strings* under *Settings*. I use the *Microsoft Entra password authentication string*. I fill in the `SqlAdmin` username and password and add it to `local.settings.json`. Before deploying, I will update this to use the Function App's managed identity.

![](2024-04-25_23-57.png)

I then set up my `main` function
```python
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
```
A request to this function will look like `http://<FUNCTION URL>?item=<ITEM NAME>`

The function first sets the `item_query` variable by pulling the value from the `item` parameter that will be sent in a GET request.

After that is an `if` Statement that says if it receives a GET request, to go to the `get_stock` function and send the necessary parameters.

Then an `elif` statement that says if it receives a POST request to extract the JSON body of the post request. If there is no body, send a 400 error.

It then sets the `item_query` and `quantity` values by reading the JSON body. If either of those are not specifies, it sends a 400 error.

After that it sends the proper parameters to the `order_item` function. 

If neither a GET or POST request are recieved, a 405 error is sent back.

Next is the `connect_with_retry` function. This function attempts a connection to the SQL database 10 times, with increasing time between tries. This is because with a serverless SQL database that "pauses" after a certain time of inactivity, it shuts down and when it receives a new request, it can take some time to boot up again.
```python
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
```

After that is the `get_stock` function, which will be used to update that amount of items in stock
```python
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
```
It receives the name of the item we want to get the stock of in the `item_query` parameter.
 
It uses the `connect_with_retry` function to connect to the SQL database. It then runs the an SQL query that returns the value of the `stock` column where the `item_name` is set to whatever item was requested. It uses parameterization in the SQL query to ensure that the input data (`item_query`) is treated strictly as data, not executable code. This way, even if the input contains SQL code, it will be treated as a plain string value within the database query. This is to avoid SQL injection.

And last is the `order_item` function
```python
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
```
It receives the name of the item and the amount to order in the `item_query` and `quantity` parameters.

It first checks that `quantity` is an integer and throws an error if it's not.

After that it uses `connect_with_retry` to connect to the database and runs a parameterized SQL query to decrement the stock of whatever item was ordered by the amount that was ordered.

To test this out, I run the function with `start func host --functions Order` and send a GET request with `curl`.  When I send a valid name, I get the proper value, and when I send a nonexistent item, I get an error.
```bash
┌──(clayton㉿Nucleus)──[15:37:00]──[~/GitRepos/ShipShape/backend/api]
└─$ curl 'http://localhost:7071/api/Order?item=droid_silicon'
100                                                                                               
┌──(clayton㉿Nucleus)──[15:57:36]──[~/GitRepos/ShipShape/backend/api]
└─$ curl 'http://localhost:7071/api/Order?item=lmao'         
Item lmao not found
```
I also send some POST requests with `curl` and I get a success message back. I then send 2 requests to test that the database was properly updated:
```bash
┌──(clayton㉿Nucleus)──[16:01:00]──[~/GitRepos/ShipShape/backend/api]
└─$ curl 'http://localhost:7071/api/Order' -d '{"item": "laser_crystals", "quantity": "10"}' -H 'Content-Type: application/json'
Order for laser_crystals placed successfully                                                                                               

┌──(clayton㉿Nucleus)──[16:01:38]──[~/GitRepos/ShipShape/backend/api]
└─$ curl 'http://localhost:7071/api/Order' -d '{"item": "rations", "quantity": "18"}' -H 'Content-Type: application/json'
Order for rations placed successfully

┌──(clayton㉿Nucleus)──[15:37:00]──[~/GitRepos/ShipShape/backend/api]
└─$ curl 'http://localhost:7071/api/Order?item=laser_crystals'
90
┌──(clayton㉿Nucleus)──[15:37:00]──[~/GitRepos/ShipShape/backend/api]
└─$ curl 'http://localhost:7071/api/Order?item=rations'
82
```
I'm pretty confident in the parameterized SQL statements, but just to be sure I attempt some manual SQL injection, and then run [SQLMap](https://github.com/sqlmapproject/sqlmap) against it with `--leve=5`, `--risk=5` and a few tamper scripts. No SQL injection was picked up.
### Integrating with Website
Now I need to integrate this with the website. I'll do this by modifying the html and writing a new javascript file. Now again, I am no web developer and so it's important to keep in mind that this is likely not the most optimized way to handle the HTML and CSS. I grab some images and add them to my `images` directory. I then create a flex container and add all the images and their captions into it. I then use an `input` tag for users to specify the quantity, and `button` tag to create an order button. I also add a paragraph with `p` tag that will display while the function is getting the inventory details. The `p` tag will be updated by the Javascript with the current stock. What I end up with for my resupply.html page is this:
```html
<section class="slider_section position-relative">
  <div class="container-fluid">
    <div id="carouselExampleIndicators" class="carousel slide" data-ride="carousel">
      <div class="carousel-inner">
        <div class="row justify-content-center align-items-center">
          <div class="col-md-8 text-center">
            <div class="detail-box">
              <h2>
                Resupply
              </h2>
              <div class="container">
                <div class="resupply-flex-container">
                  <div class="resupply-item">
                    <img src="images/rations.jpg" height="300" width="auto">
                    <p>Rations</p>
                    <p id="stock_rations">In stock: Loading...</p>
                    <input type="number" id="rationQty" name="rationQty" min="1" placeholder="Qty">
                    <button onclick="orderItem('Rations', rationQty.value)">Order</button>
                    <div id="message_rations" class="form-text" style="font-size: 24px; text-align: center; color: green; min-height: 40px;"></div>
                  </div>
                  <div class="resupply-item">
                    <img src="images/laser_crystal.jpg" height="300" width="auto">
                    <p>Laser Crystals</p>
                    <p id="stock_laser_crystals">In stock: Loading...</p>
                    <input type="number" id="laserCrystalQty" name="laserCrystalQty" min="1" placeholder="Qty">
                    <button onclick="orderItem('laser_crystals', laserCrystalQty.value)">Order</button>
                    <div id="message_laser_crystals" class="form-text" style="font-size: 24px; text-align: center; color: green; min-height: 40px;"></div>
                  </div>
                  <div class="resupply-item">
                    <img src="images/silicon_wafer.png" height="300" width="auto">
                    <p>Droid Silicon</p>
                    <p id="stock_droid_silicon">In stock: Loading...</p>
                    <input type="number" id="droidSiliconQty" name="droidSiliconQty" min="1" placeholder="Qty">
                    <button onclick="orderItem('droid_silicon', droidSiliconQty.value)">Order</button>
                    <div id="message_droid_silicon" class="form-text" style="font-size: 24px; text-align: center; color: green; min-height: 40px;"></div>
                  </div>
                  <div class="resupply-item">
                    <img src="images/capacitor.jpeg" height="300" width="auto">
                    <p>Capacitors</p>
                    <p id="stock_capacitors">In stock: Loading...</p>
                    <input type="number" id="capacitorQty" name="capacitorQty" min="1" placeholder="Qty">
                    <button onclick="orderItem('capacitors', capacitorQty.value)">Order</button>
                    <div id="message_capacitors" class="form-text" style="font-size: 24px; text-align: center; color: green; min-height: 40px;"></div>
                  </div>
                  <div class="resupply-item">
                    <img src="images/fuel.jpeg" height="300" width="auto">
                    <p>Rocket Fuel</p>
                    <p id="stock_fuel">In stock: Loading...</p>
                    <input type="number" id="rocketFuelQty" name="rocketFuelQty" min="1" placeholder="Qty">
                    <button onclick="orderItem('fuel', rocketFuelQty.value)">Order</button>
                    <div id="message_fuel" class="form-text" style="font-size: 24px; text-align: center; color: green; min-height: 40px;"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
    </div>
  </div>
</section>
```
Also at the very bottom of the page right before </body> and </html> I add a script source
```html
<script src="js/order.js"></script>
</body>
</html>
```

I also add these lines to my `style.css` to configure the flex container as well as the styling.
```css
.resupply-flex-container {
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: center;
  outline: none;
}

.resupply-item {
  margin: 0 10px;
  text-align: center;
  outline: none;
}

.resupply-item a {
  color: #ffffff;
}
.resupply-item a:hover {
  color: #00ff00;
  text-decoration: underline;
}
```
The page currently looks like this

![](2024-04-25_16-11.png)

I create a file in `js/order.js`
```js
document.addEventListener('DOMContentLoaded', function() {
  updateStock('Rations', 'stock_rations');
  updateStock('laser_crystals', 'stock_laser_crystals');
  updateStock('droid_silicon', 'stock_droid_silicon');
  updateStock('capacitors', 'stock_capacitors');
  updateStock('fuel', 'stock_fuel');
});

const localFunctionUrl  = 'https://shipshapefa.azurewebsites.net/api/order'

function updateStock(itemName, elementId) {
  fetch(`${localFunctionUrl}?item=${encodeURIComponent(itemName)}`)
      .then(response => response.json())
      .then(data => {
          document.getElementById(elementId).innerText = `In stock: ${data}`;
      })
      .catch(error => {
          console.error('Failed to fetch stock data:', error);
          document.getElementById(elementId).innerText = 'In stock: Unavailable';
      });
}

function orderItem(itemName, quantity) {
  const itemKey = itemName.toLowerCase().replace(/ /g, '_');
  var messageDiv = document.getElementById('message_' + itemKey);
  messageDiv.textContent = "Processing order..."

  const data = { item: itemName, quantity: quantity };
  

  fetch(localFunctionUrl, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {
      'Content-Type': 'application/json'
    }
  })

  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.text();
  })
  .then(data => {
    console.log(data);
    let elementId = 'stock_' + itemName.toLowerCase().replace(' ', '_'); // Assuming the itemName format needs adjusting
    messageDiv.textContent = ""
    updateStock(itemName.toLowerCase(), elementId);
  })
  .catch(error => {
    console.log(`Failed to order ${quantity} of ${itemName}: ${error}`);
  });
}
```
The Javascript starts with an event listener for `DOMContentLoaded`, which means the script will run on page load.
This script works by setting values for `rations`, `laser_crystals` etc. by getting the values of `stockRations`, `stockLaserCrystals` from the html.

It then sets a variable for `localFunctionUrl` to the address the function runs on locally.

After that is the `updateStock` function. It sends GET request to the function url containing the item name in a query parameter. This will cause the function to query the database the retrieve the stock of that item. The `updateStock` function then extracts that data from the response and updates the section of the html corresponding to that item. This will run every time the page is loaded.

Last is the `orderItem` function. This will set the `json` body format in the `data` variable.

Once this function starts a message is displayed below the item stating the order is being process. It then sends a POST request to the function URL with a `json` body containing the item name and amount to be ordered. If no error is received, it then runs the `updateStock` function for the item that was just ordered.

After this, I reload my site, and I see the proper item amounts from my database!

![](2024-04-25_16-19.png)

I try the order function and sure enough, the site updates to reflect the correct amount in the database. In the developer console I can see the POST request to the function as well as the following GET request

![](2024-04-25_22-54.png)
## Deploying to Azure
After this, all I need to do is deploy everything to azure. I first deploy my functions by going to the *Workspace* section in the Azure extension and clicking the lightning icon, I then select *Deploy to Function App*. I point it to my *ShipShapeFA* function app and let it deploy.

Once deployed, I grab the function URLs from the azure portal and update my javascript to point to the right place. Once this is done, I run a `git push` and wait for everything to deploy.

Once this is done I browse to my site and make sure everything is working. All the item stocks load on the resupply page, and my orders go through

![](2024-04-30_14-52.png)
 
 I also test out the file upload and everything works there too. I get my SAS URL, the file is renamed properly, I get my email, and all my network infrastructure and VMs deploy.
 
![](2024-04-30_14-53.png)

# Conclusion
This was a great project for me. I got experience in a lot of different areas including managing permissions and identities, using SDKs to integrate Azure functions with other services, setting up a CI/CD pipeline with Github workflows, writing deployment templates using `bicep`, automatic deployment using ARM templates, and managing compute resources and network infrastructure. I feel like I generally learn much better by getting hands on with things. And so it's been great to take a break from studying and reading about these concepts and actually take them for a spin myself.