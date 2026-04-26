// GDPR consent banner
(function () {
    if (!localStorage.getItem('gdpr_accepted')) {
        var banner = document.getElementById('gdpr-banner');
        if (banner) banner.style.display = 'flex';
    }
})();

function acceptGDPR() {
    localStorage.setItem('gdpr_accepted', '1');
    var banner = document.getElementById('gdpr-banner');
    if (banner) banner.style.display = 'none';
}

function toggleAlerta() {
    const form = document.getElementById('forma-alerta');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function salveazaAlerta(produsId) {
    const email = document.getElementById('email').value;
    const pretDorit = document.getElementById('pret-dorit').value;
    const msg = document.getElementById('alerta-msg');

    const gdprCheck = document.getElementById('gdpr-alerta');
    if (!email || !pretDorit) {
        msg.textContent = '⚠️ Completează email și prețul dorit!';
        msg.style.color = 'red';
        return;
    }
    if (!gdprCheck.checked) {
        msg.textContent = '⚠️ Trebuie să accepți Politica de Confidențialitate pentru a seta alerta.';
        msg.style.color = 'red';
        return;
    }

    const formData = new FormData();
    formData.append('produs_id', produsId);
    formData.append('email', email);
    formData.append('pret_dorit', pretDorit);

    try {
        const r = await fetch('/alerta', { method: 'POST', body: formData });
        const data = await r.json();
        msg.textContent = data.mesaj;
        msg.style.color = data.status === 'ok' ? 'green' : 'red';
    } catch (e) {
        msg.textContent = '❌ Eroare la salvare!';
        msg.style.color = 'red';
    }
}
