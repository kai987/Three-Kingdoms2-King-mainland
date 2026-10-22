# Self-hosted cloud SDK

The game serves the official `@supabase/supabase-js` browser SDK locally. There is no runtime CDN dependency. Runtime and build versions are pinned in `package.json` and `package-lock.json`; bundled source, checksums, and complete runtime licenses are committed under `game/vendor/`.

```sh
npm ci --prefix tools/cloud-sdk --ignore-scripts
npm run build --prefix tools/cloud-sdk
npm run check --prefix tools/cloud-sdk
```

Only `GameSupabase.createClient` is exported. Cloud Auth uses a game-specific storage key, email/password login, and local sign-out; it does not consume other applications' URL sessions or global Auth storage.

References: [password-based Auth](https://supabase.com/docs/guides/auth/passwords), [JavaScript client](https://supabase.com/docs/reference/javascript/initializing), [Auth state events](https://supabase.com/docs/reference/javascript/auth-onauthstatechange).
