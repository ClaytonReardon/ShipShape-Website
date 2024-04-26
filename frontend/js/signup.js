document.addEventListener('DOMContentLoaded', function() {
    var signupForm = document.getElementById('signup-form');

    signupForm.addEventListener('submit', function(event) {
        event.preventDefault();

        // Get username and password from the form
        var username = document.getElementById('username').value;
        var password = document.getElementById('password').value;
        var passwordConfirm = document.getElementById('passwordConfirm').value;

        // Check if passwords match
        if (password !== passwordConfirm) {
            alert("Passwords do not match.");
            return; // Don't submit form
        }

        // Create POST request to send data to Azure function
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'http://localhost:7071/api/Account', true);
        xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4 && xhr.status === 201) {
                alert('User created succesfully!');
            } else if (xhr.readyState === 4) {
                alert('Error creating user: ' + xhr.responseText);
            }
        };

        // Send the POST request with user data
        xhr.send(JSON.stringify({username: username, password: password}));
    });
});