// https://getbootstrap.com/docs/5.3/forms/validation/
    document.querySelector("form").addEventListener("submit", function(e) {
        var password = document.getElementById("password").value;
        var confirm = document.getElementById("confirm_password");
 
        if (password !== confirm.value) {
            e.preventDefault();
            confirm.classList.add("is-invalid");
        } else {
            confirm.classList.remove("is-invalid");
        }
    });