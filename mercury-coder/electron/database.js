const Database = require('better-sqlite3');
const path = require('path');
const { app } = require('electron');

class ProjectDatabase {
  constructor() {
    const dbPath = path.join(app.getPath('userData'), 'mercury-coder.db');
    this.db = new Database(dbPath);
    this.initTables();
  }

  initTables() {
    // Projects table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        path TEXT NOT NULL UNIQUE,
        description TEXT,
        last_opened DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Project settings/metadata
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS project_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value TEXT,
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
        UNIQUE(project_id, key)
      )
    `);

    // Recent files per project
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS recent_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        last_opened DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
      )
    `);

    // Open tabs per project
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS open_tabs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        order_index INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
      )
    `);
  }

  // Project methods
  addProject(name, projectPath, description = null) {
    const stmt = this.db.prepare(`
      INSERT INTO projects (name, path, description, last_opened)
      VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    `);
    return stmt.run(name, projectPath, description);
  }

  getProjects() {
    return this.db.prepare(`
      SELECT * FROM projects 
      ORDER BY last_opened DESC
    `).all();
  }

  getProject(projectId) {
    return this.db.prepare('SELECT * FROM projects WHERE id = ?').get(projectId);
  }

  openProject(projectId) {
    const stmt = this.db.prepare(`
      UPDATE projects 
      SET last_opened = CURRENT_TIMESTAMP 
      WHERE id = ?
    `);
    stmt.run(projectId);
    return this.getProject(projectId);
  }

  deleteProject(projectId) {
    const stmt = this.db.prepare('DELETE FROM projects WHERE id = ?');
    return stmt.run(projectId);
  }

  // Recent files methods
  addRecentFile(projectId, filePath) {
    // Remove old entry if exists
    this.db.prepare(`
      DELETE FROM recent_files 
      WHERE project_id = ? AND file_path = ?
    `).run(projectId, filePath);

    // Insert new entry
    const stmt = this.db.prepare(`
      INSERT INTO recent_files (project_id, file_path, last_opened)
      VALUES (?, ?, CURRENT_TIMESTAMP)
    `);
    return stmt.run(projectId, filePath);
  }

  getRecentFiles(projectId, limit = 10) {
    return this.db.prepare(`
      SELECT * FROM recent_files 
      WHERE project_id = ? 
      ORDER BY last_opened DESC 
      LIMIT ?
    `).all(projectId, limit);
  }

  // Settings methods
  setSetting(projectId, key, value) {
    const stmt = this.db.prepare(`
      INSERT INTO project_settings (project_id, key, value)
      VALUES (?, ?, ?)
      ON CONFLICT(project_id, key) DO UPDATE SET value = excluded.value
    `);
    return stmt.run(projectId, key, value);
  }

  getSetting(projectId, key) {
    const result = this.db.prepare(`
      SELECT value FROM project_settings 
      WHERE project_id = ? AND key = ?
    `).get(projectId, key);
    return result ? result.value : null;
  }

  close() {
    this.db.close();
  }
}

module.exports = ProjectDatabase;









































