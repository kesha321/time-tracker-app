// Clock In
function clockIn() {
    fetch('/clock-in', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams({
        fullname: document.getElementById('fullname').value,
        role: document.getElementById('role').value,
        timezone: getTimezone()
      })
    })
    .then(res => res.json())
    .then(data => document.getElementById('status').innerText = data.message)
    .catch(err => document.getElementById('status').innerText = 'An error occurred.');
  }
  
  // Clock Out
  function clockOut() {
    fetch('/clock-out', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams({
        fullname: document.getElementById('fullname').value
      })
    })
    .then(res => res.json())
    .then(data => document.getElementById('status').innerText = data.message)
    .catch(err => document.getElementById('status').innerText = 'An error occurred.');
  }
  