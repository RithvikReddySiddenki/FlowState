import { cp, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

// Next's standalone output intentionally omits static/public assets. Assemble
// them for host-run production/browser tests just as the Dockerfile does.
await mkdir(".next/standalone/.next", { recursive: true });
await cp(".next/static", ".next/standalone/.next/static", { recursive: true });
await cp("public", ".next/standalone/public", { recursive: true });
process.env.HOSTNAME ||= "127.0.0.1";
process.env.PORT ||= "3000";
await import(pathToFileURL(resolve(".next/standalone/server.js")).href);
