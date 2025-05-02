const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const moment = require('moment'); // For calculating duration without timezone conversion
const path = require('path');
require('dotenv').config({ path: __dirname + '/.env' });

console.log("🧪 MONGODB_URI from .env:", process.env.MONGODB_URI);

const app = express();

// Enable CORS for all origins
app.use(cors());

// Middleware to parse JSON in the request body
app.use(express.json());

// MongoDB Connection
mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log("✅ MongoDB connected"))
  .catch(err => console.log("❌ MongoDB connection error: ", err));

// TimeEntry model
const TimeEntry = require('./backend/models/TimeEntry');

// Utility: Calculate total time
const calculateTotalTime = (startTime, endTime) => {
  const start = moment(startTime);
  const end = moment(endTime);

  if (!start.isValid() || !end.isValid()) {
    throw new Error("Invalid date format for startTime or endTime");
  }

  const totalMinutes = end.diff(start, 'minutes');
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours} Hours ${minutes} Minutes`;
};

// === API Routes ===

// POST: Add time entry
app.post('/time-entry', async (req, res) => {
  try {
    const { user, startTime, endTime } = req.body;

    if (!user || !startTime || !endTime) {
      return res.status(400).json({ message: "Missing required fields: user, startTime, or endTime" });
    }

    const totalTime = calculateTotalTime(startTime, endTime);

    const newTimeEntry = new TimeEntry({ user, startTime, endTime, totalTime });
    await newTimeEntry.save();
    res.status(201).json(newTimeEntry);
  } catch (err) {
    res.status(400).json({ message: 'Error adding time entry', error: err.message });
  }
});

// GET: All entries
app.get('/time-entries', async (req, res) => {
  try {
    const entries = await TimeEntry.find({});
    res.json(entries);
  } catch (err) {
    res.status(500).json({ message: 'Error retrieving entries', error: err.message });
  }
});

// PUT: Update entry
app.put('/time-entry/:id', async (req, res) => {
  try {
    const { user, startTime, endTime } = req.body;

    if (!user || !startTime || !endTime) {
      return res.status(400).json({ message: "Missing required fields: user, startTime, or endTime" });
    }

    const totalTime = calculateTotalTime(startTime, endTime);

    const updated = await TimeEntry.findByIdAndUpdate(
      req.params.id,
      { user, startTime, endTime, totalTime },
      { new: true }
    );

    if (!updated) {
      return res.status(404).json({ message: 'Time entry not found' });
    }

    res.json(updated);
  } catch (err) {
    res.status(500).json({ message: 'Error updating time entry', error: err.message });
  }
});

// DELETE: Remove entry
app.delete('/time-entry/:id', async (req, res) => {
  try {
    const deleted = await TimeEntry.findByIdAndDelete(req.params.id);
    if (!deleted) {
      return res.status(404).json({ message: 'Time entry not found' });
    }
    res.json({ message: 'Time entry deleted successfully', deleted });
  } catch (err) {
    res.status(500).json({ message: 'Error deleting time entry', error: err.message });
  }
});

// === Serve Static Frontend Files ===
app.use(express.static(path.join(__dirname, '../frontend')));

// Catch-all: Send index.html for unknown routes (for SPA support or fallback)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

// === Start Server ===
const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
