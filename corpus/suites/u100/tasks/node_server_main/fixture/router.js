function Router() {
  this.routes = {};
}

Router.prototype.addRoute = function(method, path, handler) {
  var key = method.toUpperCase() + ' ' + path;
  this.routes[key] = handler;
};

Router.prototype.match = function(method, path) {
  var key = method.toUpperCase() + ' ' + path;
  return this.routes[key] || null;
};

module.exports = Router;
