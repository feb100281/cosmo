document.addEventListener('DOMContentLoaded', function() {
    // Function for the first button
    document.getElementById('fletch_egrul').addEventListener('click', function() {
        var taxIdValue = document.getElementById('id_tax_id').value;  // Note the 'id_' prefix

        // Check if the tax_id is not blank
        if (!taxIdValue) {
            alert("Введите ИНН"); // Alert user if tax_id is empty
            return; // Exit the function if tax_id is blank
        }

        fetch(`https://api.checko.ru/v2/company?key=SIwfo6CFilGM4fUX&inn=${taxIdValue}`)
        .then(response => {
            // Check if the response is ok (status in the range 200-299)
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json(); // Parse JSON if the response is successful
        })
        .then(data => {
            let contragentName = data.data['НаимСокр'];
            // Replace " with ''
            contragentName = contragentName.replace(/"/g, "");
            // Split the string by spaces
            let parts = contragentName.split(' ');

            // Rearrange parts: move the first part to the end
            if (parts.length > 1) {
                const firstPart = parts.shift(); // Remove the first part
                parts.push(firstPart); // Add it to the end
            }
            contragentName = parts.join(' ');
            document.getElementById('id_name').value = contragentName;
            document.getElementById('id_ogrn').value = String(data.data['ОГРН']);
            document.getElementById('id_kpp').value = String(data.data['КПП']);
            document.getElementById('id_region').value = data.data['Регион']['Наим'];
            document.getElementById('id_adress').value = data.data['ЮрАдрес']['АдресРФ'];
            document.getElementById('id_fullname').value = data.data['НаимПолн'];
            if (data.data['Руковод'] && data.data['Руковод'].length > 0) {
                document.getElementById('id_ceo').value = data.data['Руковод'][0]['ФИО'];
            }
            document.getElementById('id_website').value = data.data['Контакты']['ВебСайт'];
            const phoneNumbers = data.data['Контакты']['Тел'];
            const phoneNumbersString = phoneNumbers.join(', ');
            const emailAdress = data.data['Контакты']['Емэйл'];
            const emailAdressString = emailAdress.join(', ');
            const taxRegime = data.data['Налоги']['ОсобРежим'];
            const taxRegimeAdressString = taxRegime.join(', ');
            document.getElementById('id_email').value = emailAdressString;
            document.getElementById('id_tel').value = phoneNumbersString;
            document.getElementById('id_taxregime').value = taxRegimeAdressString;

        })
        .catch(error => {
            console.error('Error:', error); // Handle any errors
            alert('Failed to fetch data: ' + error.message);
        });
});
// EGRIP
document.getElementById('fletch_egrip').addEventListener('click', function() {
    var taxIdValue = document.getElementById('id_tax_id').value;  // Note the 'id_' prefix

    // Check if the tax_id is not blank
    if (!taxIdValue) {
        alert("Введите ИНН"); // Alert user if tax_id is empty
        return; // Exit the function if tax_id is blank
    }

    fetch(`https://api.checko.ru/v2/entrepreneur?key=SIwfo6CFilGM4fUX&inn=${taxIdValue}`)
    .then(response => {
        // Check if the response is ok (status in the range 200-299)
        if (!response.ok) {
            throw new Error('Network response was not ok ' + response.statusText);
        }
        return response.json(); // Parse JSON if the response is successful
    })
    .then(data => {
        let contragentName = data.data['ФИО'];
        let contragentNameadj = contragentName.toUpperCase() + ' ИП';
        document.getElementById('id_name').value = contragentNameadj;
        document.getElementById('id_ogrn').value = String(data.data['ОГРНИП']);
        document.getElementById('id_kpp').value = String(data.data['ОКПО']);
        document.getElementById('id_region').value = data.data['Регион']['Наим'];
        document.getElementById('id_adress').value = data.data['НасПункт'];
        document.getElementById('id_fullname').value = contragentNameadj;
        document.getElementById('id_ceo').value = contragentName;
    })
    .catch(error => {
        console.error('Error:', error); // Handle any errors
        alert('Failed to fetch data: ' + error.message);
    });
});

});
