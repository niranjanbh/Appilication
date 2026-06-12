const SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

// Static export has no Next.js server, so the form-proxy route handlers under
// app/api/ never ship to ./out — this map is the production equivalent of them.
// Every proxied form call is Turnstile-verified; phone OTP on the booking flow
// is an optional extra gate (backend KYROS_BOOKING_OTP_ENABLED).
const FORM_PROXY_ROUTES = {
  "/api/contact": "/v1/public/lead",
  "/api/book/send-otp": "/v1/public/booking-otp",
  "/api/book": "/v1/public/booking-inquiry",
};

function jsonResponse(data, status) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function verifyTurnstileToken(token, secret, remoteIp) {
  if (!secret) return true; // not configured — don't block submissions
  if (typeof token !== "string" || token.length === 0) return false;

  const body = new URLSearchParams({ secret, response: token });
  if (remoteIp) body.append("remoteip", remoteIp);

  try {
    const resp = await fetch(SITEVERIFY_URL, { method: "POST", body });
    const outcome = await resp.json();
    return outcome && outcome.success === true;
  } catch {
    return false;
  }
}

async function handleFormProxy(request, env, backendPath) {
  let payload;
  try {
    payload = await request.json();
  } catch {
    return jsonResponse({ detail: "Invalid request body." }, 400);
  }

  const { turnstileToken, ...body } = payload ?? {};
  const remoteIp = request.headers.get("CF-Connecting-IP");

  const verified = await verifyTurnstileToken(turnstileToken, env.TURNSTILE_SECRET_KEY, remoteIp);
  if (!verified) {
    return jsonResponse({ detail: "We could not verify your request. Please try again." }, 403);
  }

  const backendUrl = env.BACKEND_URL;
  if (!backendUrl) {
    return jsonResponse({ detail: "Could not reach the server. Please try again." }, 503);
  }

  try {
    const resp = await fetch(`${backendUrl}${backendPath}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await resp.json().catch(() => ({ ok: resp.ok }));
    return jsonResponse(data, resp.status);
  } catch {
    return jsonResponse({ detail: "Could not reach the server. Please try again." }, 503);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "POST" && FORM_PROXY_ROUTES[url.pathname]) {
      return handleFormProxy(request, env, FORM_PROXY_ROUTES[url.pathname]);
    }

    const response = await env.ASSETS.fetch(request);

    const newResponse = new Response(response.body, response);
    newResponse.headers.set("X-Frame-Options", "DENY");
    newResponse.headers.set("X-Content-Type-Options", "nosniff");
    newResponse.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
    newResponse.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
    newResponse.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload");

    return newResponse;
  },
};
