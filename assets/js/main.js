document.addEventListener('DOMContentLoaded', function() {

    const mobileMenuButton = document.createElement('button');
    mobileMenuButton.className = 'mobile-menu-button';
    mobileMenuButton.innerHTML = '☰';
    
    const navbar = document.querySelector('.navbar');
    const navLinks = document.querySelector('.nav-links');
    const navCenter = document.querySelector('.nav-center');
    
    if (window.innerWidth <= 768) {
        navbar.insertBefore(mobileMenuButton, navCenter);
        navLinks.style.display = 'none';
    }
    
    mobileMenuButton.addEventListener('click', function() {
        navLinks.style.display = navLinks.style.display === 'none' ? 'flex' : 'none';
    });
    
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            navLinks.style.display = 'flex';
            if (mobileMenuButton.parentNode) {
                navbar.removeChild(mobileMenuButton);
            }
        } else {
            if (!mobileMenuButton.parentNode) {
                navbar.insertBefore(mobileMenuButton, navCenter);
                navLinks.style.display = 'none';
            }
        }
    });

    // Фильтры
    const rangeSlider = document.querySelector('input[type="range"]');
    if (rangeSlider) {
        rangeSlider.addEventListener('input', function() {
            const value = (this.value - this.min) / (this.max - this.min) * 100;
            this.style.background = `linear-gradient(to right, var(--primary-color) ${value}%, #ddd ${value}%)`;
        });
    }

    
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    
    const currentPage = location.pathname.split('/').pop().replace('.html', '');
    if (currentPage) {
        const navItems = document.querySelectorAll('.nav-links a');
        navItems.forEach(item => {
            if (item.getAttribute('href').includes(currentPage)) {
                item.classList.add('active');
            }
        });
    }
});

document.addEventListener('click', function(e) {
    const dropdown = document.querySelector('.account-dropdown');
    if (!dropdown.contains(e.target)) {
        document.querySelector('.dropdown-menu').style.display = 'none';
    }
});

document.addEventListener('DOMContentLoaded', function () {

    // Удаляю обработчик перехода на /chats для .respond-button-new, чтобы работало только модальное окно отклика

    document.querySelector('.message-button')?.addEventListener('click', function (e) {
        window.location.href = '/chats';
    });
});

// ====== ЧАТ: динамический offer и звук ======
window.addEventListener('DOMContentLoaded', function() {
    const offerBlock = document.getElementById('offer-block');
    const offerSound = document.getElementById('offer-sound');
    let lastOfferId = null;
    let lastMsgId = 0;
    const chatId = window.location.pathname.split('/').filter(Boolean).pop();
    const currentUserId = window.currentUserId || null;
    async function pollOffer() {
        try {
            const resp = await fetch(`/chat/${chatId}/messages?after_id=0`);
            if (!resp.ok) return;
            const messages = await resp.json();
            // ищем последний offer
            const offers = messages.filter(m => m.type === 'offer');
            if (offers.length) {
                const offer = offers[offers.length-1];
                if (offer.id !== lastOfferId) {
                    lastOfferId = offer.id;
                    offerBlock.innerHTML = `<div class='chat-message-offer' style='background:#fffbe6; border:1.5px solid #ffe066; border-radius:10px; padding:1.2em 1.5em; margin:1.2em 0;'>
                        <b>Отклик на заказ!</b><br>
                        <div style='margin:0.7em 0 0.5em 0;'>${offer.text}</div>
                        <button class='apply-filters' style='margin-top:0.7em;'>Принять заказ</button>
                    </div>`;
                    if (offerSound) offerSound.play();
                }
            } else {
                offerBlock.innerHTML = '';
                lastOfferId = null;
            }
            // звук на любое новое сообщение (кроме своих)
            if (messages.length) {
                const lastMsg = messages[messages.length-1];
                if (lastMsg.id !== lastMsgId && (!currentUserId || lastMsg.sender_id != currentUserId)) {
                    lastMsgId = lastMsg.id;
                    if (offerSound) offerSound.play();
                }
            }
        } catch(e) {}
    }
    if (offerBlock) setInterval(pollOffer, 2000);
});

// ====== Автоматическая разблокировка звука ======
window.addEventListener('DOMContentLoaded', function() {
    let soundUnlocked = false;
    function unlockSound() {
        if (!soundUnlocked) {
            const audio = document.getElementById('offer-sound');
            if (audio) audio.play().catch(()=>{});
            soundUnlocked = true;
            document.removeEventListener('click', unlockSound, true);
            document.removeEventListener('focusin', unlockSound, true);
        }
    }
    document.addEventListener('click', unlockSound, true);
    document.addEventListener('focusin', unlockSound, true);
});