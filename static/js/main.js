// General Web Interactions - PS-TEX Saree Store

document.addEventListener('DOMContentLoaded', () => {
    // Password Confirmation Checker for Forms
    const regForm = document.querySelector('form[action*="register"]');
    if (regForm) {
        const passwordInput = regForm.querySelector('input[name="password"]');
        const confirmInput = regForm.querySelector('input[name="confirm_password"]');
        
        const checkPasswords = () => {
            if (passwordInput.value !== confirmInput.value) {
                confirmInput.setCustomValidity("Passwords do not match");
            } else {
                confirmInput.setCustomValidity("");
            }
        };
        
        passwordInput.addEventListener('change', checkPasswords);
        confirmInput.addEventListener('keyup', checkPasswords);
    }
    
    // Auto Fade Out Flash Alert messages
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade');
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);
    });
    
    // Smooth scroll for anchor links
    const scrollLinks = document.querySelectorAll('a[href^="#"]');
    scrollLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const targetEl = document.querySelector(targetId);
            if (targetEl) {
                e.preventDefault();
                targetEl.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});
