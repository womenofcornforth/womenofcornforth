function menuIcon() {
    var curIcon = document.getElementsByClassName("menu-icon");
    
    switch (curIcon.innerHTML){
        case "☰":
            var newIcon = "X"
            break;
        case "X":
            var newIcon = "☰"
            break;
        default:
            console.log(curIcon);
    }
    
    document.getElementsByClassName("menu-icon").innerHTML = newIcon;
}

// toggle navbar on mobile
function toggleMenu() {
    var navLinks = document.getElementById("navLinks");
    navLinks.classList.toggle("active");
    menuIcon();
}
