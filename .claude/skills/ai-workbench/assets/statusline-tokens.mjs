#!/usr/bin/env node
// Session token totals for the status line: sums message usage from the session transcript.
// Claude Code's own payload only reports the current context size, not session totals.
// Reads only bytes added since the last run (cached per transcript), so refreshes stay cheap.
// Usage: node statusline-tokens.mjs <transcript_path>  ->  prints "in 12.3M 97% cached  out 85k"
import { createHash } from "node:crypto";
import { closeSync, mkdirSync, openSync, readFileSync, readSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const transcript = process.argv[2];
if (!transcript) process.exit(0);

const dir = join(homedir(), ".cache", "claude-statusline");
const cacheFile = join(dir, createHash("sha1").update(transcript).digest("hex") + ".json");
let c = { offset: 0, fresh: 0, cached: 0, out: 0, lastId: null, last: [0, 0, 0] };
try {
  c = JSON.parse(readFileSync(cacheFile, "utf8"));
} catch {}

let size;
try {
  size = statSync(transcript).size;
} catch {
  process.exit(0);
}
if (size < c.offset) c = { offset: 0, fresh: 0, cached: 0, out: 0, lastId: null, last: [0, 0, 0] }; // file was replaced

if (size > c.offset) {
  const fd = openSync(transcript, "r");
  const buf = Buffer.alloc(size - c.offset);
  readSync(fd, buf, 0, buf.length, c.offset);
  closeSync(fd);
  const text = buf.toString("utf8");
  const end = text.lastIndexOf("\n") + 1; // leave a half-written last line for next time
  for (const line of text.slice(0, end).split("\n")) {
    if (!line.includes('"usage"')) continue;
    let m;
    try {
      m = JSON.parse(line).message;
    } catch {
      continue;
    }
    const u = m?.usage;
    if (!u) continue;
    const row = [(u.input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0), u.cache_read_input_tokens ?? 0, u.output_tokens ?? 0];
    // One API response is logged once per content block, all with the same id: count it once, using its latest usage.
    if (m.id && m.id === c.lastId) {
      c.fresh -= c.last[0];
      c.cached -= c.last[1];
      c.out -= c.last[2];
    }
    c.fresh += row[0];
    c.cached += row[1];
    c.out += row[2];
    c.lastId = m.id ?? null;
    c.last = row;
  }
  c.offset += Buffer.byteLength(text.slice(0, end), "utf8");
  mkdirSync(dir, { recursive: true });
  writeFileSync(cacheFile, JSON.stringify(c));
}

const fmt = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? Math.round(n / 1e3) + "k" : String(n));
const total = c.fresh + c.cached;
if (total) console.log(`in ${fmt(total)} ${Math.round((c.cached / total) * 100)}% cached  out ${fmt(c.out)}`);
