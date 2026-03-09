function toggleDropdown() {
    var dropdown = document.getElementById("avatarDropdown");
    dropdown.classList.toggle("show");
}

document.addEventListener("click", function(e) {
    var wrapper = document.querySelector(".avatar-wrapper");
    if (wrapper && !wrapper.contains(e.target)) {
        document.getElementById("avatarDropdown").classList.remove("show");
    }
});