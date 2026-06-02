# Playground

Run datamodel-code-generator in your browser. The deployed site serves this route as a standalone app so Pyodide only starts after you open it.

The playground runs entirely in your browser with Pyodide. Your schema, selected input type, and options are passed to
the local Pyodide worker for generation and are not posted to a backend server.

Use **Copy Repro URL** in the playground to share the current input schema, input type, and selected options in the URL fragment.
When a playground version is selected, **Copy Repro URL** keeps the selected `?version=` in the shared URL.
The fragment part (`#state=...`) is client-side URL state and is not included in HTTP requests, so the encoded schema and
options are not sent to the hosting server or Cloudflare by opening the link. The complete URL, including the fragment,
can still be stored in local browser history and is visible to anyone or any service you share it with. The optional
`?version=` query parameter is sent in normal page requests, so hosting/CDN metrics can record the selected playground
version but not the encoded schema or options.

<p>
  <a class="md-button md-button--primary" href="../assets/playground/index.html">Open Playground</a>
</p>
