function toggleAlerta() {
    const form = document.getElementById('forma-alerta');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function salveazaAlerta(produsId) {
    const email = document.getElementById('email').value;
    const pretDorit = document.getElementById('pret-dorit').value;
    const msg = document.getElementById('alerta-msg');

    if (!email || !pretDorit) {
        msg.textContent = '⚠️ Completează email și prețul dorit!';
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
