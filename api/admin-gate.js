const { authorizeAdmin } = require("../lib/booking/admin");

module.exports = function handler(request, response) {
  const result = authorizeAdmin(request.headers.authorization || "", process.env);
  response.setHeader("cache-control", "no-store");
  return response.status(result.status).json(result.body);
};
