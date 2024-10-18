function menuIcon() {
    var curIcon = document.getElementById("iconstr");
    var iconText = curIcon.innerHTML
    switch (iconText){
        case "☰":
            var newIcon = "x"
            break;
        case "x":
            var newIcon = "☰"
            break;
        default:
            console.log(iconText);
    }
        
    curIcon.innerHTML = newIcon;
}

// toggle navbar on mobile
function toggleMenu() {
    var navLinks = document.getElementById("navLinks");
    navLinks.classList.toggle("active");
    menuIcon();
}
