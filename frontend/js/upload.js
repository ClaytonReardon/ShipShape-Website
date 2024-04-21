const localFunctionUrl = "https://shipshapefa.azurewebsites.net/api/FileUpload?code=SHnTCQ3i-svUW4j2hBGC1UON5_-YxvTT4Ytl6aR62ZbwAzFuosLhww==";

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
