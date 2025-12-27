document.addEventListener('DOMContentLoaded', () => {
    const tableConfigs = [
        { id: 'exams', file: '../context_tables/exams.csv', title: 'Exams Schedule' },
        { id: 'lectures', file: '../context_tables/lectures.csv', title: 'Lectures' },
        { id: 'course_description', file: '../context_tables/course_description.csv', title: 'Course Descriptions' },
        { id: 'course_masterlist', file: '../context_tables/course_masterlist.csv', title: 'Course Masterlist' }
    ];

    const mainContainer = document.getElementById('dashboard-grid');

    tableConfigs.forEach(config => {
        // Create Card Structure
        const card = document.createElement('div');
        card.className = 'table-card';
        card.innerHTML = `
            <div class="card-header">
                <h2>${config.title}</h2>
            </div>
            <div class="table-container" id="container-${config.id}">
                <div class="loading">Loading...</div>
            </div>
        `;
        mainContainer.appendChild(card);

        // Fetch and Render CSV
        fetch(config.file)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.text();
            })
            .then(csvText => {
                const data = parseCSV(csvText);
                renderTable(data, `container-${config.id}`);
            })
            .catch(error => {
                console.error('Error fetching CSV:', error);
                document.getElementById(`container-${config.id}`).innerHTML = `
                    <div style="padding: 1rem; color: #ef4444;">
                        Error loading data: ${error.message}
                    </div>`;
            });
    });
});

function parseCSV(text) {
    // A simple CSV parser that defines rows by newlines and columns by commas
    // Handles quoted fields relatively simply (assuming standard CSV format)
    const lines = text.trim().split('\n');
    return lines.map(line => {
        const row = [];
        let inQuotes = false;
        let currentValue = '';

        for (let i = 0; i < line.length; i++) {
            const char = line[i];

            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                row.push(currentValue.trim());
                currentValue = '';
            } else {
                currentValue += char;
            }
        }
        row.push(currentValue.trim()); // Push last value

        // Remove surrounding quotes if present
        return row.map(cell => {
            if (cell.startsWith('"') && cell.endsWith('"')) {
                return cell.slice(1, -1).replace(/""/g, '"');
            }
            return cell;
        });
    });
}

function renderTable(data, containerId) {
    if (data.length === 0) return;

    const headers = data[0];
    const rows = data.slice(1);

    const table = document.createElement('table');

    // Create Header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create Body
    const tbody = document.createElement('tbody');
    rows.forEach(rowData => {
        // Skip empty rows
        if (rowData.length === 1 && rowData[0] === '') return;

        const tr = document.createElement('tr');
        rowData.forEach(cellData => {
            const td = document.createElement('td');
            td.textContent = cellData;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    const container = document.getElementById(containerId);
    container.innerHTML = ''; // Clear loading
    container.appendChild(table);
}
