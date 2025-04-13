const mongoose = require('mongoose');

const timeEntrySchema = new mongoose.Schema({
  user: {
    type: String,
    required: true,
  },
  startTime: {
    type: String,  // Changed from Date to String
    required: true,
  },
  endTime: {
    type: String,  // Changed from Date to String
    required: true,
  },
  totalTime: {
    type: String,
    required: true,
  },
});

const TimeEntry = mongoose.model('TimeEntry', timeEntrySchema);

module.exports = TimeEntry;
