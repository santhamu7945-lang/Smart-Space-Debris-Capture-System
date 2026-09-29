/* =========================================================
   ADCS GLOBAL NAVIGATION SYSTEM
========================================================= */


document.addEventListener("DOMContentLoaded", () => {

    const navigation = document.createElement("nav");

    navigation.className = "site-navigation";


    navigation.innerHTML = `

        <a href="index.html" class="nav-brand">

            <div class="brand-mark">
                <span>AD</span>
            </div>

            <div class="brand-text">

                <span class="brand-title">
                    ADCS
                </span>

                <span class="brand-subtitle">
                    Orbital Operations
                </span>

            </div>

        </a>


        <button class="nav-toggle"
                aria-label="Toggle Navigation">

            ☰

        </button>


        <div class="nav-links">

            <a href="index.html">
                Home
            </a>

            <a href="system_operation.html">
                Mission Dossier
            </a>

            <a href="index.html">
                Flight Operations Center
            </a>

            <a href="simulation.html">
                OrbitView
            </a>

            <a href="simulation.html">
                Live Simulation
            </a>

        </div>

    `;


    document.body.prepend(navigation);


    /* ============================================
       ACTIVE PAGE DETECTION
    ============================================ */

    const currentPage =
        window.location.pathname
            .split("/")
            .pop()
            || "index.html";


    const links =
        navigation.querySelectorAll(".nav-links a");


    links.forEach(link => {

        const href =
            link.getAttribute("href");


        if(href === currentPage){

            link.classList.add("active");

        }

    });


    /* ============================================
       MOBILE NAVIGATION
    ============================================ */

    const toggle =
        navigation.querySelector(".nav-toggle");


    const navLinks =
        navigation.querySelector(".nav-links");


    toggle.addEventListener("click", () => {

        navLinks.classList.toggle("open");

    });


    /* ============================================
       CLOSE MOBILE NAVIGATION
    ============================================ */

    links.forEach(link => {

        link.addEventListener("click", () => {

            navLinks.classList.remove("open");

        });

    });

});