export default {
  async fetch(request, env) {
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
