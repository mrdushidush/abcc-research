function logRequest(method, path, status, durationMs) {
  if (durationMs === undefined) durationMs = 0;
  return method + ' ' + path + ' -> ' + status + ' (' + durationMs + 'ms)';
}

function corsHeaders(origin) {
  if (origin === undefined) origin = '*';
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };
}

module.exports = { logRequest, corsHeaders };
