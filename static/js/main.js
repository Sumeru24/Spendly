// main.js — students will add JavaScript here as features are built

(function () {
    var modal = document.getElementById('how-it-works-modal');
    if (!modal) return;

    var openBtn = document.getElementById('how-it-works-btn');
    var closeBtn = document.getElementById('how-it-works-close');
    var video = document.getElementById('how-it-works-video');

    function openModal() {
        modal.classList.add('is-open');
        document.body.classList.add('modal-open');
        if (video && video.dataset.src) {
            video.src = video.dataset.src + '?autoplay=1&rel=0';
        }
    }

    function closeModal() {
        modal.classList.remove('is-open');
        document.body.classList.remove('modal-open');
        if (video) {
            video.src = '';
        }
    }

    if (openBtn) {
        openBtn.addEventListener('click', openModal);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    modal.addEventListener('click', function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && modal.classList.contains('is-open')) {
            closeModal();
        }
    });
})();
