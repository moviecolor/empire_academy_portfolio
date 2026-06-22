const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;
const DATA_FILE = path.join(__dirname, 'courses.json');

// ─── Middleware ─────────────────────────────────────────────
app.use(cors());                     // Allow browser frontend to call API
app.use(express.json());             // Parse JSON request bodies

// Serve the Empire dashboard as the default page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'evil-empire-dashboard.html'));
});
// Redirect anyone hitting the old index.html to the Empire dashboard
app.get('/index.html', (req, res) => {
  res.redirect(301, '/');
});

app.use(express.static(__dirname));  // Serve static files (SVGs, etc.)

// ─── Helpers ────────────────────────────────────────────────

/** Read courses from JSON file */
function readCourses() {
  const raw = fs.readFileSync(DATA_FILE, 'utf-8');
  const data = JSON.parse(raw);
  return data.courses || [];
}

/** Write courses to JSON file */
function writeCourses(courses) {
  fs.writeFileSync(DATA_FILE, JSON.stringify({ courses }, null, 2), 'utf-8');
}

/** Find next available ID */
function nextId(courses) {
  if (courses.length === 0) return 1;
  return Math.max(...courses.map(c => c.id)) + 1;
}

/** Consistent JSON response format */
function jsonResponse(res, status, data, message = null) {
  const body = { status, data };
  if (message) body.message = message;
  return res.status(status).json(body);
}

/** Validation rules for course fields */
const VALID_STATUSES = ['active', 'archived', 'draft'];
const VALID_DIFFICULTIES = ['beginner', 'intermediate', 'advanced', 'expert'];
const VALID_CATEGORIES = [
  'flight-systems', 'infrastructure', 'weapons-systems', 'networking',
  'embedded-systems', 'robotics', 'data-engineering', 'game-dev',
  'project-management', 'cybersecurity'
];

function validateCourse(body, isUpdate = false) {
  const errors = [];

  if (!isUpdate || body.title !== undefined) {
    if (!body.title || typeof body.title !== 'string' || body.title.trim().length === 0) {
      errors.push('title is required and must be a non-empty string');
    }
  }

  if (!isUpdate || body.description !== undefined) {
    if (!body.description || typeof body.description !== 'string' || body.description.trim().length === 0) {
      errors.push('description is required and must be a non-empty string');
    }
  }

  if (!isUpdate || body.instructor !== undefined) {
    if (!body.instructor || typeof body.instructor !== 'string' || body.instructor.trim().length === 0) {
      errors.push('instructor is required and must be a non-empty string');
    }
  }

  if (!isUpdate || body.difficulty !== undefined) {
    if (!body.difficulty || !VALID_DIFFICULTIES.includes(body.difficulty)) {
      errors.push(`difficulty must be one of: ${VALID_DIFFICULTIES.join(', ')}`);
    }
  }

  if (!isUpdate || body.category !== undefined) {
    if (!body.category || !VALID_CATEGORIES.includes(body.category)) {
      errors.push(`category must be one of: ${VALID_CATEGORIES.join(', ')}`);
    }
  }

  if (!isUpdate || body.status !== undefined) {
    if (!body.status || !VALID_STATUSES.includes(body.status)) {
      errors.push(`status must be one of: ${VALID_STATUSES.join(', ')}`);
    }
  }

  return errors;
}

// ─── CRUD Routes ────────────────────────────────────────────

/** GET /api/courses — List all courses */
app.get('/api/courses', (req, res) => {
  try {
    const courses = readCourses();
    return jsonResponse(res, 200, courses);
  } catch (err) {
    return jsonResponse(res, 500, null, 'Failed to read courses data');
  }
});

/** GET /api/courses/search?q=term — Search courses (must be before :id route) */
app.get('/api/courses/search', (req, res) => {
  try {
    const query = (req.query.q || '').toLowerCase().trim();
    if (!query) {
      return jsonResponse(res, 400, null, 'Query parameter "q" is required');
    }

    const courses = readCourses();
    const results = courses.filter(c =>
      c.title.toLowerCase().includes(query) ||
      c.description.toLowerCase().includes(query) ||
      c.instructor.toLowerCase().includes(query)
    );

    return jsonResponse(res, 200, results);
  } catch (err) {
    return jsonResponse(res, 500, null, 'Search failed');
  }
});

/** GET /api/courses/:id — Get a single course by ID */
app.get('/api/courses/:id', (req, res) => {
  try {
    const courses = readCourses();
    const id = parseInt(req.params.id, 10);
    const course = courses.find(c => c.id === id);

    if (!course) {
      return jsonResponse(res, 404, null, `Course with id ${id} not found`);
    }

    return jsonResponse(res, 200, course);
  } catch (err) {
    return jsonResponse(res, 500, null, 'Failed to read course');
  }
});

/** POST /api/courses — Create a new course */
app.post('/api/courses', (req, res) => {
  try {
    const errors = validateCourse(req.body);
    if (errors.length > 0) {
      return jsonResponse(res, 400, null, errors.join('; '));
    }

    const courses = readCourses();
    const now = new Date().toISOString();

    const newCourse = {
      id: nextId(courses),
      title: req.body.title.trim(),
      description: req.body.description.trim(),
      instructor: req.body.instructor.trim(),
      difficulty: req.body.difficulty,
      category: req.body.category,
      status: req.body.status || 'draft',
      createdAt: now,
      updatedAt: now
    };

    courses.push(newCourse);
    writeCourses(courses);

    return jsonResponse(res, 201, newCourse, 'Course created successfully');
  } catch (err) {
    return jsonResponse(res, 500, null, 'Failed to create course');
  }
});

/** PUT /api/courses/:id — Update an existing course */
app.put('/api/courses/:id', (req, res) => {
  try {
    const courses = readCourses();
    const id = parseInt(req.params.id, 10);
    const index = courses.findIndex(c => c.id === id);

    if (index === -1) {
      return jsonResponse(res, 404, null, `Course with id ${id} not found`);
    }

    // Allow partial updates — only validate fields that are provided
    const errors = validateCourse(req.body, true);
    if (errors.length > 0) {
      return jsonResponse(res, 400, null, errors.join('; '));
    }

    const now = new Date().toISOString();
    const updated = {
      ...courses[index],
      ...req.body,
      id: courses[index].id,       // Don't allow ID change
      createdAt: courses[index].createdAt,  // Preserve original creation date
      updatedAt: now
    };

    // Trim string fields if provided
    if (req.body.title) updated.title = req.body.title.trim();
    if (req.body.description) updated.description = req.body.description.trim();
    if (req.body.instructor) updated.instructor = req.body.instructor.trim();

    courses[index] = updated;
    writeCourses(courses);

    return jsonResponse(res, 200, updated, 'Course updated successfully');
  } catch (err) {
    return jsonResponse(res, 500, null, 'Failed to update course');
  }
});

/** DELETE /api/courses/:id — Delete a course */
app.delete('/api/courses/:id', (req, res) => {
  try {
    const courses = readCourses();
    const id = parseInt(req.params.id, 10);
    const index = courses.findIndex(c => c.id === id);

    if (index === -1) {
      return jsonResponse(res, 404, null, `Course with id ${id} not found`);
    }

    const deleted = courses.splice(index, 1)[0];
    writeCourses(courses);

    return jsonResponse(res, 200, deleted, 'Course deleted successfully');
  } catch (err) {
    return jsonResponse(res, 500, null, 'Failed to delete course');
  }
});

/** GET /api/stats — Course statistics (bonus) */
app.get('/api/stats', (req, res) => {
  try {
    const courses = readCourses();
    const stats = {
      total: courses.length,
      byStatus: {},
      byDifficulty: {},
      byCategory: {}
    };

    courses.forEach(c => {
      stats.byStatus[c.status] = (stats.byStatus[c.status] || 0) + 1;
      stats.byDifficulty[c.difficulty] = (stats.byDifficulty[c.difficulty] || 0) + 1;
      stats.byCategory[c.category] = (stats.byCategory[c.category] || 0) + 1;
    });

    return jsonResponse(res, 200, stats);
  } catch (err) {
    return jsonResponse(res, 500, null, 'Failed to compute stats');
  }
});

// ─── Start Server ───────────────────────────────────────────
app.listen(PORT, () => {
  console.log('╔══════════════════════════════════════════════════╗');
  console.log('║   ⚙️  EVIL EMPIRE ACADEMY — CODING SERVER  ⚙️   ║');
  console.log('╠══════════════════════════════════════════════════╣');
  console.log(`║  API:        http://localhost:${PORT}/api/courses  ║`);
  console.log(`║  Stats:      http://localhost:${PORT}/api/stats    ║`);
  console.log(`║  Search:     http://localhost:${PORT}/api/courses/search?q=  ║`);
  console.log('║  Frontend:   http://localhost:3000                ║');
  console.log('╚══════════════════════════════════════════════════╝');
});
