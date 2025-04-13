let clockInTime = null;

const nameInput = document.getElementById("name");
const roleSelect = document.getElementById("role");
const clockInBtn = document.getElementById("clockInBtn");
const clockOutBtn = document.getElementById("clockOutBtn");

// 🕒 Live Clock
function updateClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// ✅ Enable/Disable Clock In/Out buttons
function checkFields() {
  const nameFilled = nameInput.value.trim() !== "";
  const roleSelected = roleSelect.value !== "";
  clockInBtn.disabled = !(nameFilled && roleSelected);
  clockOutBtn.disabled = !(nameFilled && roleSelected);
}
nameInput.addEventListener("input", checkFields);
roleSelect.addEventListener("change", checkFields);

// ✅ Restore clock-in time from localStorage
window.addEventListener("load", () => {
  const savedTime = localStorage.getItem("clockInTime");
  if (savedTime) {
    clockInTime = new Date(savedTime);
    showToast("Restored clock-in time: " + clockInTime.toLocaleTimeString());
  }
  loadTimeEntries();
});

// ✅ Clock In
clockInBtn.addEventListener("click", () => {
  clockInTime = new Date();
  localStorage.setItem("clockInTime", clockInTime.toISOString());
  showToast("Clocked in at: " + clockInTime.toLocaleTimeString());
});

// ✅ Clock Out
clockOutBtn.addEventListener("click", async () => {
  const name = nameInput.value.trim();
  const role = roleSelect.value;

  if (!name || !role) {
    alert("Please fill out all required fields.");
    return;
  }

  if (!clockInTime) {
    alert("You must clock in first!");
    return;
  }

  const clockOutTime = new Date();

  const payload = {
    user: `${name} (${role})`,
    startTime: clockInTime,
    endTime: clockOutTime
  };

  try {
    const response = await fetch("/time-entry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (response.ok) {
      showToast("Time entry saved successfully!");
      loadTimeEntries();
      localStorage.removeItem("clockInTime");
      clockInTime = null;
    } else {
      alert("Failed to save time entry: " + result.message);
    }
  } catch (error) {
    console.error("Error:", error);
    alert("Something went wrong while saving the time entry.");
  }
});

// ✅ Toast Notification
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.classList.add("show");

  setTimeout(() => {
    toast.classList.remove("show");
    toast.classList.add("hidden");
  }, 3000);
}

// ✅ Load entries from backend
async function loadTimeEntries() {
  try {
    const response = await fetch("/time-entries");
    const entries = await response.json();
    displayEntries(entries);
  } catch (error) {
    console.error("Error fetching time entries:", error);
    document.getElementById("timeEntries").innerHTML = "<p>Error loading entries.</p>";
  }
}

// ✅ Format total time
function formatDuration(ms) {
  const totalMinutes = Math.floor(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours}h ${minutes}m`;
}

// ✅ Display entries
function displayEntries(entries) {
  const entriesContainer = document.getElementById("timeEntries");
  if (!entries || entries.length === 0) {
    entriesContainer.innerHTML = "<p>No time entries found.</p>";
    return;
  }

  let html = `
    <table>
      <thead>
        <tr>
          <th>User</th>
          <th>Start Time</th>
          <th>End Time</th>
          <th>Total Time</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
  `;

  entries.forEach(entry => {
    const start = new Date(entry.startTime);
    const end = new Date(entry.endTime);
    const duration = end - start;
    html += `
      <tr>
        <td>${entry.user}</td>
        <td>${start.toLocaleString()}</td>
        <td>${end.toLocaleString()}</td>
        <td>${formatDuration(duration)}</td>
        <td><button onclick="deleteEntry('${entry._id}')">Delete</button></td>
      </tr>
    `;
  });

  html += "</tbody></table>";
  entriesContainer.innerHTML = html;
}

// ✅ Delete entry by ID
async function deleteEntry(id) {
  if (!confirm("Are you sure you want to delete this entry?")) return;
  try {
    const response = await fetch(`/time-entry/${id}`, {
      method: "DELETE"
    });
    const result = await response.json();
    if (response.ok) {
      showToast("Entry deleted successfully.");
      loadTimeEntries();
    } else {
      alert("Failed to delete entry: " + result.message);
    }
  } catch (error) {
    console.error("Error deleting entry:", error);
    alert("Error occurred while deleting the entry.");
  }
}
