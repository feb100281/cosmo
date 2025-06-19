function formatDate(dateStr) {
    if (!dateStr) return null;
    let parts = dateStr.split(".");
    return `${parts[2]}-${parts[1]}-${parts[0]}`;  // Преобразуем в YYYY-MM-DD
}

document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("load_structures").addEventListener("click", function() {
        let docIdRaw = document.querySelector(".readonly")?.innerText.trim();
        
        // Если значение равно "-" или пустое, передаем null
        let docId = (docIdRaw === "-" || docIdRaw === "") ? null : docIdRaw;

        console.log("ID перед отправкой:", docId);

        // Собираем данные из формы
        let data = {
            id: docId,
            lease_agreement_id: document.getElementById("id_lease_agreement")?.value || null,
            doc_number: document.getElementById("id_doc_number")?.value || null,
            doc_date: formatDate(document.getElementById("id_doc_date")?.value),
            doc_title_id: document.getElementById("id_doc_title")?.value || null,
            start_date: formatDate(document.getElementById("id_start_date")?.value),
            end_date: formatDate(document.getElementById("id_end_date")?.value),
            rr_structure_id: document.getElementById("id_rr_structure")?.value || null,
            la_terms_id: document.getElementById("id_la_terms")?.value || null,
            terms: document.getElementById("id_terms")?.value || "{}"
        };

        fetch("/la/save-document/", {
            method: "POST",
            body: JSON.stringify(data),
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log("Ответ сервера:", data);
            alert(data.message);

            if (!docId) {
                // Если создавался новый документ, перенаправляем на редактирование
                window.location.href = `/admin/la/documents/${data.doc_id}/change/`;
            }
        })
        .catch(error => console.error("Ошибка:", error));
    });
});

document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("load_terms").addEventListener("click", function() {
        let docIdRaw = document.querySelector(".readonly")?.innerText.trim();
        
        // Если значение равно "-" или пустое, передаем null
        let docId = (docIdRaw === "-" || docIdRaw === "") ? null : docIdRaw;

        console.log("ID перед отправкой:", docId);

        // Собираем данные из формы
        let data = {
            id: docId,
            lease_agreement_id: document.getElementById("id_lease_agreement")?.value || null,
            doc_number: document.getElementById("id_doc_number")?.value || null,
            doc_date: formatDate(document.getElementById("id_doc_date")?.value),
            doc_title_id: document.getElementById("id_doc_title")?.value || null,
            start_date: formatDate(document.getElementById("id_start_date")?.value),
            end_date: formatDate(document.getElementById("id_end_date")?.value),
            rr_structure_id: document.getElementById("id_rr_structure")?.value || null,
            la_terms_id: document.getElementById("id_la_terms")?.value || null,
            terms: document.getElementById("id_terms")?.value || "{}"
        };

        fetch("/la/get-document/", {
            method: "POST",
            body: JSON.stringify(data),
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log("Ответ сервера:", data);
            alert(data.message);

            if (!docId) {
                // Если создавался новый документ, перенаправляем на редактирование
                window.location.href = `/admin/la/documents/${data.doc_id}/change/`;
            }
        })
        .catch(error => console.error("Ошибка:", error));
    });
});