const localFunctionUrl = "http://localhost:7071/api/fileupload";

// upload.js
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('upload-form').addEventListener('submit', function(event) {
        event.preventDefault();

        const fileInput = document.getElementById('starshipReport');
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        fetch(localFunctionUrl, {
            method: 'POST',
            // Optional headers removed for simplicity
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);
            alert('File uploaded successfully!');
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error uploading file.');
        });
    });
});
