function authorizeAdmin(header, env) {
  const expected = env.ADMIN_ACCESS_TOKEN;
  if (!expected) {
    return { status: 503, body: { ok: false, reason: "not_configured" } };
  }
  if (header !== `Bearer ${expected}`) {
    return { status: 401, body: { ok: false, reason: "unauthorized" } };
  }
  return { status: 200, body: { ok: true } };
}

module.exports = { authorizeAdmin };
