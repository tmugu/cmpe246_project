const initialData = window.dashboardData || {
    summary: {},
    users: [],
    attendance: [],
    chartData: { labels: [], granted: [], denied: [] },
};

const usersTableBody = document.getElementById("users-table-body");
const attendanceTableBody = document.getElementById("attendance-table-body");
const formStatus = document.getElementById("form-status");
const refreshButton = document.getElementById("refresh-dashboard");
const userForm = document.getElementById("user-form");
const latestScanTag = document.getElementById("latest-scan-tag");

let attendanceChart;

function setFormStatus(message, isError = false) {
    if (!formStatus) {
        return;
    }

    formStatus.textContent = message;
    formStatus.classList.toggle("is-error", isError);
}

function badgeClass(status) {
    return status === "granted" ? "status-pill granted" : "status-pill denied";
}

function userStatusClass(isActive) {
    return isActive ? "status-pill granted" : "status-pill denied";
}

function renderSummary(summary) {
    document.getElementById("metric-total-users").textContent = summary.total_users ?? 0;
    document.getElementById("metric-active-users").textContent = summary.active_users ?? 0;
    document.getElementById("metric-granted-today").textContent = summary.granted_today ?? 0;
    document.getElementById("metric-denied-today").textContent = summary.denied_today ?? 0;
    latestScanTag.textContent = `Last scan: ${summary.latest_scan_at || "No scans yet"}`;
}

function renderUsers(users) {
    usersTableBody.innerHTML = "";

    if (!users.length) {
        usersTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">No RFID users registered yet.</td>
            </tr>
        `;
        return;
    }

    for (const user of users) {
        const row = document.createElement("tr");
        const activeLabel = user.is_active ? "Active" : "Inactive";

        row.innerHTML = `
            <td>${user.name}</td>
            <td><code>${user.rfid_uid}</code></td>
            <td class="caps">${user.role}</td>
            <td><span class="${userStatusClass(Boolean(user.is_active))}">${activeLabel}</span></td>
            <td class="actions-cell">
                <button class="table-action" data-action="toggle" data-user-id="${user.id}" data-current-state="${user.is_active}">
                    ${user.is_active ? "Disable" : "Enable"}
                </button>
                <button class="table-action danger" data-action="delete" data-user-id="${user.id}">
                    Delete
                </button>
            </td>
        `;

        usersTableBody.appendChild(row);
    }
}

function renderAttendance(attendance) {
    attendanceTableBody.innerHTML = "";

    if (!attendance.length) {
        attendanceTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">No attendance records yet.</td>
            </tr>
        `;
        return;
    }

    for (const row of attendance) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.created_at}</td>
            <td>${row.person_name}</td>
            <td><code>${row.rfid_uid}</code></td>
            <td><span class="${badgeClass(row.status)}">${row.status}</span></td>
            <td>${row.note || ""}</td>
        `;
        attendanceTableBody.appendChild(tr);
    }
}

function renderChart(chartData) {
    const canvas = document.getElementById("attendance-chart");
    if (!canvas) {
        return;
    }

    if (attendanceChart) {
        attendanceChart.destroy();
    }

    attendanceChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: "Granted",
                    data: chartData.granted,
                    backgroundColor: "#1fd1a5",
                    borderRadius: 8,
                },
                {
                    label: "Denied",
                    data: chartData.denied,
                    backgroundColor: "#ff6b57",
                    borderRadius: 8,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: "#d9ecff",
                        font: { family: "Space Grotesk" },
                    },
                },
            },
            scales: {
                x: {
                    ticks: {
                        color: "#c7d8ea",
                        font: { family: "IBM Plex Mono" },
                    },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: "#c7d8ea",
                        font: { family: "IBM Plex Mono" },
                    },
                    grid: {
                        color: "rgba(151, 176, 202, 0.12)",
                    },
                },
            },
        },
    });
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }

    return data;
}

async function refreshDashboard() {
    try {
        const [summary, users, attendance, chartData] = await Promise.all([
            fetchJson("/api/summary"),
            fetchJson("/api/users"),
            fetchJson("/api/attendance?limit=20"),
            fetchJson("/api/charts/attendance?days=7"),
        ]);

        renderSummary(summary);
        renderUsers(users);
        renderAttendance(attendance);
        renderChart(chartData);
        setFormStatus("Dashboard refreshed.");
    } catch (error) {
        setFormStatus(error.message, true);
    }
}

async function handleUserAction(event) {
    const button = event.target.closest("button[data-action]");
    if (!button) {
        return;
    }

    const userId = button.dataset.userId;
    const action = button.dataset.action;

    try {
        if (action === "toggle") {
            const nextActiveValue = button.dataset.currentState !== "1";
            await fetchJson(`/api/users/${userId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ is_active: nextActiveValue }),
            });
            setFormStatus("User access status updated.");
        }

        if (action === "delete") {
            await fetchJson(`/api/users/${userId}`, {
                method: "DELETE",
            });
            setFormStatus("User removed from the system.");
        }

        await refreshDashboard();
    } catch (error) {
        setFormStatus(error.message, true);
    }
}

async function handleCreateUser(event) {
    event.preventDefault();

    const formData = new FormData(userForm);
    const payload = {
        name: formData.get("name"),
        rfid_uid: formData.get("rfid_uid"),
        role: formData.get("role"),
        is_active: formData.get("is_active") === "on",
    };

    try {
        await fetchJson("/api/users", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        userForm.reset();
        userForm.querySelector('input[name="is_active"]').checked = true;
        setFormStatus("User registered successfully.");
        await refreshDashboard();
    } catch (error) {
        setFormStatus(error.message, true);
    }
}

renderSummary(initialData.summary);
renderUsers(initialData.users);
renderAttendance(initialData.attendance);
renderChart(initialData.chartData);

userForm.addEventListener("submit", handleCreateUser);
usersTableBody.addEventListener("click", handleUserAction);
refreshButton.addEventListener("click", refreshDashboard);

window.setInterval(refreshDashboard, 20000);
