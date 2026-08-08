function NoteStore() {
  this._notes = {};
  this._nextId = 1;
}

NoteStore.prototype.create = function(title, content) {
  var note = { id: this._nextId, title: title, content: content || '' };
  this._notes[this._nextId] = note;
  this._nextId++;
  return note;
};

NoteStore.prototype.get = function(id) {
  return this._notes[id] || null;
};

NoteStore.prototype.listAll = function() {
  var self = this;
  return Object.keys(this._notes).map(function(k) { return self._notes[k]; });
};

NoteStore.prototype.remove = function(id) {
  if (this._notes[id]) { delete this._notes[id]; return true; }
  return false;
};

module.exports = NoteStore;
